import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from app.config_loader import (
    ConfigLoader,
    ConfigurationError,
)
from app.result_aggregator.summary_builder import (
    KubernetesSummaryBuilder,
    SummaryBuilderError,
)
from app.writers.csv_writer import (
    CsvWriter,
    CsvWriterError,
)


SUMMARY_BUILDER_REGISTRY = {
    "kubernetes": KubernetesSummaryBuilder,
}


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate entity-level and pod-level "
            "statistics CSV files."
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
        help="Generate summary for only one component",
    )

    return parser


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


def load_reporting_config(
    file_path: str = "config/reporting.yaml",
) -> dict[str, Any]:
    """Load reporting configuration used only by summary generation."""

    reporting_file = Path(file_path)

    if not reporting_file.is_file():
        raise SummaryBuilderError(
            "Reporting configuration was not found: "
            f"{reporting_file.resolve()}"
        )

    try:
        with reporting_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            result = yaml.safe_load(file) or {}

    except yaml.YAMLError as exc:
        raise SummaryBuilderError(
            f"Invalid YAML in '{reporting_file}': {exc}"
        ) from exc

    except OSError as exc:
        raise SummaryBuilderError(
            f"Could not read '{reporting_file}': {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise SummaryBuilderError(
            "reporting.yaml must contain a YAML dictionary."
        )

    return result


def get_summary_config(
    reporting_config: dict[str, Any],
) -> dict[str, Any]:
    """Return the reporting.summaries configuration section."""

    reporting_root = reporting_config.get(
        "reporting",
        {},
    )

    if not isinstance(reporting_root, dict):
        raise SummaryBuilderError(
            "'reporting' must be a dictionary in reporting.yaml."
        )

    summary_config = reporting_root.get(
        "summaries",
        {},
    )

    if not isinstance(summary_config, dict):
        raise SummaryBuilderError(
            "'reporting.summaries' must be a dictionary."
        )

    return summary_config


def get_csv_output_config(
    summary_config: dict[str, Any],
    section_name: str,
    default_file_name: str,
) -> dict[str, Any]:
    """Validate one configured summary CSV output section."""

    output_config = summary_config.get(
        section_name,
        {},
    )

    if not isinstance(output_config, dict):
        raise SummaryBuilderError(
            f"'reporting.summaries.{section_name}' "
            "must be a dictionary."
        )

    enabled = output_config.get("enabled", True)

    if not isinstance(enabled, bool):
        raise SummaryBuilderError(
            f"'{section_name}.enabled' must be true or false."
        )

    columns = output_config.get(
        "columns",
        [],
    )

    if enabled:
        if not isinstance(columns, list) or not columns:
            raise SummaryBuilderError(
                f"'{section_name}.columns' must be a "
                "non-empty list."
            )

        invalid_columns = [
            column
            for column in columns
            if not isinstance(column, str) or not column.strip()
        ]

        if invalid_columns:
            raise SummaryBuilderError(
                f"Every value in '{section_name}.columns' "
                "must be a non-empty string."
            )

    file_name = output_config.get(
        "file_name",
        default_file_name,
    )

    if not isinstance(file_name, str) or not file_name.strip():
        raise SummaryBuilderError(
            f"'{section_name}.file_name' must be a "
            "non-empty string."
        )

    return {
        "enabled": enabled,
        "columns": columns,
        "file_name": file_name,
    }


def build_summary_collector_config(
    collector_config: dict[str, Any],
    summary_config: dict[str, Any],
) -> dict[str, Any]:
    """
    Build an aggregation-only metric configuration.

    The collector configuration itself is not modified. Raw and normalized
    outputs continue to retain every metric configured for collection.
    """

    collector_metrics = collector_config.get(
        "metrics",
        {},
    )

    reporting_metrics = summary_config.get(
        "metrics",
        {},
    )

    if not isinstance(collector_metrics, dict):
        raise SummaryBuilderError(
            "Collector metrics configuration is invalid."
        )

    if not isinstance(reporting_metrics, dict):
        raise SummaryBuilderError(
            "'reporting.summaries.metrics' must be a dictionary."
        )

    selected_metrics: dict[str, dict[str, Any]] = {}

    for metric_name, reporting_metric_config in (
        reporting_metrics.items()
    ):
        if not isinstance(reporting_metric_config, dict):
            continue

        if reporting_metric_config.get("enabled", False) is not True:
            continue

        collector_metric_config = collector_metrics.get(
            metric_name
        )

        if not isinstance(collector_metric_config, dict):
            raise SummaryBuilderError(
                f"Metric '{metric_name}' is enabled in reporting.yaml "
                "but is not defined in collector_types.yaml."
            )

        selected_metrics[metric_name] = {
            **collector_metric_config,
            "display_name": reporting_metric_config.get(
                "display_name",
                collector_metric_config.get(
                    "display_name",
                    metric_name,
                ),
            ),
            "component_aggregation": reporting_metric_config.get(
                "component_aggregation",
                collector_metric_config.get(
                    "component_aggregation",
                    "avg",
                ),
            ),
        }

    if not selected_metrics:
        raise SummaryBuilderError(
            "No summary metrics are enabled under "
            "'reporting.summaries.metrics'."
        )

    return {
        **collector_config,
        "metrics": selected_metrics,
    }


def apply_readable_metric_names(
    rows: list[dict[str, Any]],
    metric_configs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Replace technical metric keys with configured display names."""

    formatted_rows: list[dict[str, Any]] = []

    for original_row in rows:
        row = dict(original_row)
        metric_name = row.get("metric_name")

        if (
            isinstance(metric_name, str)
            and metric_name in metric_configs
        ):
            row["metric_name"] = metric_configs[
                metric_name
            ].get(
                "display_name",
                metric_name,
            )

        formatted_rows.append(row)

    return formatted_rows


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
        files = [
            entity_directory
            / component_name
            / "timeseries.json"
        ]
    else:
        files = sorted(
            entity_directory.glob(
                "*/timeseries.json"
            )
        )

    existing_files = [
        file_path
        for file_path in files
        if file_path.is_file()
    ]

    if not existing_files:
        raise SummaryBuilderError(
            "No timeseries.json files found under "
            f"'{entity_directory}'."
        )

    return existing_files


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
        raise SummaryBuilderError(
            f"Invalid JSON file: {file_path}"
        ) from exc

    except OSError as exc:
        raise SummaryBuilderError(
            f"Could not read '{file_path}': {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise SummaryBuilderError(
            f"Expected JSON object in '{file_path}'."
        )

    return result


def main() -> None:
    args = build_argument_parser().parse_args()

    try:
        config_loader = ConfigLoader()

        application_config = (
            config_loader.load_application_config()
        )

        collector_types_config = (
            config_loader.load_collector_types()
        )

        reporting_config = load_reporting_config()
        summary_config = get_summary_config(
            reporting_config
        )

        if summary_config.get("enabled", True) is False:
            print(
                "Summary generation is disabled in reporting.yaml."
            )
            return

        entity_output_config = get_csv_output_config(
            summary_config=summary_config,
            section_name="entity_summary",
            default_file_name="entity-summary.csv",
        )

        pod_output_config = get_csv_output_config(
            summary_config=summary_config,
            section_name="pod_summary",
            default_file_name="pod-summary.csv",
        )

        collector_types = collector_types_config.get(
            "collector_types",
            collector_types_config,
        )

        if not isinstance(collector_types, dict):
            raise SummaryBuilderError(
                "Collector types configuration is invalid."
            )

        output_directory = get_output_directory(
            application_config
        )

        timeseries_files = find_timeseries_files(
            output_directory=output_directory,
            execution_id=args.execution_id,
            entity_name=args.entity,
            component_name=args.component,
        )

        csv_writer = CsvWriter(
            output_directory=output_directory
        )

        entity_summary_rows: list[dict[str, Any]] = []

        for timeseries_file in timeseries_files:
            normalized_result = read_json(
                timeseries_file
            )

            metadata = normalized_result.get(
                "metadata",
                {},
            )

            if not isinstance(metadata, dict):
                raise SummaryBuilderError(
                    f"Invalid metadata in {timeseries_file}"
                )

            component_name = str(
                metadata.get(
                    "component_name",
                    timeseries_file.parent.name,
                )
            )

            collector_type = metadata.get(
                "collector_type"
            )

            if (
                not isinstance(collector_type, str)
                or not collector_type
            ):
                raise SummaryBuilderError(
                    "collector_type is missing in "
                    f"{timeseries_file}"
                )

            builder_class = SUMMARY_BUILDER_REGISTRY.get(
                collector_type
            )

            if builder_class is None:
                raise SummaryBuilderError(
                    "No summary builder registered for "
                    f"'{collector_type}'."
                )

            collector_config = collector_types.get(
                collector_type
            )

            if not isinstance(collector_config, dict):
                raise SummaryBuilderError(
                    "Configuration not found for collector "
                    f"'{collector_type}'."
                )

            summary_collector_config = (
                build_summary_collector_config(
                    collector_config=collector_config,
                    summary_config=summary_config,
                )
            )

            summary_metric_configs = (
                summary_collector_config.get(
                    "metrics",
                    {},
                )
            )

            print(
                f"Calculating statistics: {component_name}"
            )

            builder = builder_class(
                collector_config=summary_collector_config,
                summary_config=summary_config,
            )

            _, pod_rows = (
                builder.build_pod_summary_rows(
                    normalized_result
                )
            )

            component_rows = (
                builder.build_component_summary_rows(
                    normalized_result
                )
            )

            pod_rows = apply_readable_metric_names(
                rows=pod_rows,
                metric_configs=summary_metric_configs,
            )

            component_rows = apply_readable_metric_names(
                rows=component_rows,
                metric_configs=summary_metric_configs,
            )

            pod_summary_file: Path | None = None

            if pod_output_config["enabled"]:
                pod_summary_file = (
                    csv_writer.write_pod_summary(
                        execution_id=args.execution_id,
                        entity_name=args.entity,
                        component_name=component_name,
                        rows=pod_rows,
                        columns=pod_output_config["columns"],
                        file_name=pod_output_config[
                            "file_name"
                        ],
                    )
                )

            entity_summary_rows.extend(
                component_rows
            )

            print(
                f"Pod summary rows: {len(pod_rows)}"
            )

            if pod_summary_file is not None:
                print(
                    f"Pod summary: {pod_summary_file}"
                )

        entity_summary_rows.sort(
            key=lambda row: (
                str(row.get("component_name", "")),
                str(row.get("metric_name", "")),
            )
        )

        entity_summary_file: Path | None = None

        if entity_output_config["enabled"]:
            entity_summary_file = (
                csv_writer.write_entity_summary(
                    execution_id=args.execution_id,
                    entity_name=args.entity,
                    rows=entity_summary_rows,
                    columns=entity_output_config["columns"],
                    file_name=entity_output_config[
                        "file_name"
                    ],
                )
            )

        print()
        print("Summary generation completed")
        print("----------------------------")
        print(
            "Components processed: "
            f"{len(timeseries_files)}"
        )
        print(
            "Entity summary rows: "
            f"{len(entity_summary_rows)}"
        )

        if entity_summary_file is not None:
            print(
                f"Entity summary: {entity_summary_file}"
            )

    except (
        ConfigurationError,
        SummaryBuilderError,
        CsvWriterError,
    ) as exc:
        print(
            f"Summary generation failed: {exc}"
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
