import argparse
from pathlib import Path
from typing import Any

import yaml

from app.config_loader import (
    ConfigLoader,
    ConfigurationError,
)
from app.reporting.html_report_builder import (
    HtmlReportBuilder,
    HtmlReportError,
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an HTML performance report from "
            "summary CSV files and performance graphs."
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

    return parser


def load_reporting_config(
    file_path: str = "config/reporting.yaml",
) -> dict[str, Any]:
    reporting_file = Path(file_path)

    if not reporting_file.is_file():
        raise HtmlReportError(
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
        raise HtmlReportError(
            f"Invalid reporting YAML: {exc}"
        ) from exc

    except OSError as exc:
        raise HtmlReportError(
            f"Could not read reporting configuration: "
            f"{exc}"
        ) from exc

    if not isinstance(config, dict):
        raise HtmlReportError(
            "reporting.yaml must contain a dictionary."
        )

    return config


def get_html_report_config(
    reporting_config: dict[str, Any],
) -> dict[str, Any]:
    reporting_root = reporting_config.get(
        "reporting",
        {},
    )

    if not isinstance(reporting_root, dict):
        raise HtmlReportError(
            "'reporting' must be a dictionary."
        )

    html_report_config = reporting_root.get(
        "html_report",
        {},
    )

    if not isinstance(html_report_config, dict):
        raise HtmlReportError(
            "'reporting.html_report' must be a dictionary."
        )

    return html_report_config


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

def load_rules_config(
    file_path: str = "config/rules.yaml",
) -> tuple[dict[str, Any], str | None]:
    rules_file = Path(file_path)

    if not rules_file.is_file():
        return (
            {},
            (
                "Rules configuration was not found: "
                f"{rules_file.resolve()}"
            ),
        )

    try:
        with rules_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            config = yaml.safe_load(file) or {}

    except yaml.YAMLError as exc:
        return (
            {},
            f"Invalid rules YAML: {exc}",
        )

    except OSError as exc:
        return (
            {},
            (
                "Could not read rules configuration: "
                f"{exc}"
            ),
        )

    if not isinstance(config, dict):
        return (
            {},
            "rules.yaml must contain a dictionary.",
        )

    return config, None

def main() -> None:
    args = build_argument_parser().parse_args()

    try:
        config_loader = ConfigLoader()

        application_config = (
            config_loader.load_application_config()
        )

        reporting_config = load_reporting_config()
        rules_config, rules_config_error = (
            load_rules_config()
        )

        html_report_config = get_html_report_config(
            reporting_config
        )

        if (
            html_report_config.get(
                "enabled",
                True,
            )
            is False
        ):
            print(
                "HTML report generation is disabled "
                "in reporting.yaml."
            )
            return

        output_directory = get_output_directory(
            application_config
        )

        builder = HtmlReportBuilder(
            report_config=html_report_config,
            rules_config=rules_config,
            rules_config_error=rules_config_error,
        )

        print(
            f"Generating HTML report for "
            f"{args.entity}"
        )

        report_file = builder.build_report(
            output_directory=output_directory,
            execution_id=args.execution_id,
            entity_name=args.entity,
        )

        print()
        print("HTML report generation completed")
        print("--------------------------------")
        print(f"Report: {report_file}")

    except (
        ConfigurationError,
        HtmlReportError,
    ) as exc:
        print(
            f"HTML report generation failed: {exc}"
        )

        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()