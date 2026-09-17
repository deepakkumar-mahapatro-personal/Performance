import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

from app.config_loader import (
    ConfigLoader,
    ConfigurationError,
)
from app.visualization.chart_builder import (
    ChartBuilderError,
    KubernetesChartBuilder,
)


CHART_BUILDER_REGISTRY = {
    "kubernetes": KubernetesChartBuilder,
}


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate entity-level and component-level "
            "performance reports from normalized time-series data."
        )
    )

    parser.add_argument(
        "--execution-id",
        required=True,
        help="Execution directory under output/",
    )

    parser.add_argument(
        "--entity",
        required=True,
        help="Entity name, for example item-ingestion",
    )

    parser.add_argument(
        "--component",
        required=False,
        help=(
            "Generate reports for only one component. "
            "The entity report will contain only that component."
        ),
    )

    return parser


def load_reporting_config(
    file_path: str = "config/reporting.yaml",
) -> dict[str, Any]:
    reporting_file = Path(file_path)

    if not reporting_file.is_file():
        raise ChartBuilderError(
            f"Reporting configuration was not found: "
            f"{reporting_file.resolve()}"
        )

    try:
        with reporting_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            config = yaml.safe_load(file) or {}

    except yaml.YAMLError as exc:
        raise ChartBuilderError(
            f"Invalid reporting YAML: {exc}"
        ) from exc

    except OSError as exc:
        raise ChartBuilderError(
            f"Could not read reporting configuration: "
            f"{exc}"
        ) from exc

    if not isinstance(config, dict):
        raise ChartBuilderError(
            "reporting.yaml must contain a dictionary."
        )

    return config


def get_chart_config(
    reporting_config: dict[str, Any],
) -> dict[str, Any]:
    reporting_root = reporting_config.get(
        "reporting",
        {},
    )

    if not isinstance(reporting_root, dict):
        raise ChartBuilderError(
            "'reporting' must be a dictionary."
        )

    chart_config = reporting_root.get(
        "charts",
        {},
    )

    if not isinstance(chart_config, dict):
        raise ChartBuilderError(
            "'reporting.charts' must be a dictionary."
        )

    return chart_config


def get_output_directory(
    application_config: dict[str, Any],
) -> str:
    collection_config = application_config.get(
        "collection",
        {},
    )

    if not isinstance(collection_config, dict):
        return "output"

    return str(
        collection_config.get(
            "output_directory",
            "output",
        )
    )


def find_timeseries_files(
    output_directory: str,
    execution_id: str,
    entity_name: str,
    component_name: str | None,
) -> list[Path]:
    entity_directory = (
        Path(output_directory)
        / execution_id
        / "aggregated"
        / entity_name
    )

    if component_name:
        expected_file = (
            entity_directory
            / component_name
            / "timeseries.json"
        )

        if not expected_file.is_file():
            raise ChartBuilderError(
                f"Timeseries file was not found: "
                f"{expected_file}"
            )

        return [expected_file]

    timeseries_files = sorted(
        entity_directory.glob(
            "*/timeseries.json"
        )
    )

    if not timeseries_files:
        raise ChartBuilderError(
            f"No timeseries.json files found under "
            f"'{entity_directory}'."
        )

    return timeseries_files


def read_json(
    file_path: Path,
) -> dict[str, Any]:
    try:
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            result = json.load(file)

    except json.JSONDecodeError as exc:
        raise ChartBuilderError(
            f"Invalid JSON file: {file_path}"
        ) from exc

    except OSError as exc:
        raise ChartBuilderError(
            f"Could not read '{file_path}': {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise ChartBuilderError(
            f"Expected a JSON object in "
            f"'{file_path}'."
        )

    return result


def get_collector_type(
    normalized_results: list[dict[str, Any]],
) -> str:
    collector_types: set[str] = set()

    for normalized_result in normalized_results:
        metadata = normalized_result.get(
            "metadata",
            {},
        )

        if not isinstance(metadata, dict):
            continue

        collector_type = metadata.get(
            "collector_type",
            "kubernetes",
        )

        collector_types.add(
            str(collector_type)
        )

    if not collector_types:
        return "kubernetes"

    if len(collector_types) > 1:
        raise ChartBuilderError(
            "Multiple collector types were found in the "
            f"same entity report: {sorted(collector_types)}"
        )

    return next(iter(collector_types))


def get_component_name(
    normalized_result: dict[str, Any],
    fallback_name: str,
) -> str:
    metadata = normalized_result.get(
        "metadata",
        {},
    )

    if not isinstance(metadata, dict):
        return fallback_name

    return str(
        metadata.get(
            "component_name",
            fallback_name,
        )
    )


def safe_directory_name(
    value: str,
) -> str:
    safe_value = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        value.strip(),
    )

    return safe_value.strip("-") or "component"


def main() -> None:
    args = build_argument_parser().parse_args()

    try:
        config_loader = ConfigLoader()

        application_config = (
            config_loader.load_application_config()
        )

        reporting_config = load_reporting_config()

        chart_config = get_chart_config(
            reporting_config
        )

        if chart_config.get("enabled", True) is False:
            print(
                "Chart generation is disabled in "
                "reporting.yaml."
            )
            return

        output_directory = get_output_directory(
            application_config
        )

        timeseries_files = find_timeseries_files(
            output_directory=output_directory,
            execution_id=args.execution_id,
            entity_name=args.entity,
            component_name=args.component,
        )

        normalized_results: list[
            dict[str, Any]
        ] = []

        result_files: list[
            tuple[Path, dict[str, Any]]
        ] = []

        for timeseries_file in timeseries_files:
            normalized_result = read_json(
                timeseries_file
            )

            normalized_results.append(
                normalized_result
            )

            result_files.append(
                (
                    timeseries_file,
                    normalized_result,
                )
            )

        collector_type = get_collector_type(
            normalized_results
        )

        builder_class = CHART_BUILDER_REGISTRY.get(
            collector_type
        )

        if builder_class is None:
            raise ChartBuilderError(
                f"No chart builder registered for "
                f"collector type '{collector_type}'."
            )

        builder = builder_class(
            chart_config=chart_config
        )

        visualization_root = (
            Path(output_directory)
            / args.execution_id
            / "visualizations"
            / args.entity
        )

        generated_files: list[Path] = []

        print(
            f"Generating entity report for "
            f"{args.entity}"
        )

        entity_report = builder.build_entity_report(
            normalized_results=normalized_results,
            output_directory=visualization_root,
        )

        if entity_report is not None:
            generated_files.append(entity_report)
            print(f"Entity report: {entity_report}")

        for (
            timeseries_file,
            normalized_result,
        ) in result_files:

            component_name = get_component_name(
                normalized_result=normalized_result,
                fallback_name=timeseries_file.parent.name,
            )

            component_directory = (
                visualization_root
                / safe_directory_name(component_name)
            )

            print(
                f"Generating component report: "
                f"{component_name}"
            )

            component_report = (
                builder.build_component_report(
                    normalized_result=normalized_result,
                    output_directory=component_directory,
                )
            )

            if component_report is not None:
                generated_files.append(
                    component_report
                )

                print(
                    f"Component report: "
                    f"{component_report}"
                )

        print()
        print("Chart generation completed")
        print("--------------------------")
        print(
            f"Components processed: "
            f"{len(normalized_results)}"
        )
        print(
            f"Reports generated: "
            f"{len(generated_files)}"
        )

    except (
        ConfigurationError,
        ChartBuilderError,
    ) as exc:
        print(f"Chart generation failed: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()