import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.config_loader import (
    ConfigLoader,
    ConfigurationError,
)
from app.elastic_client import ElasticClientError
from app.result_collector.base import CollectorError
from app.result_collector.main import (
    parse_iso_time,
    run_collection,
)
from app.writers.json_writer import JsonWriterError


class OrchestratorError(Exception):
    """Raised when an orchestration stage fails."""


@dataclass(frozen=True)
class ProcessingStage:
    name: str
    module_name: str


PROCESSING_STAGES = [
    ProcessingStage(
        name="Normalization",
        module_name="app.result_aggregator.main",
    ),
    ProcessingStage(
        name="Summary Generation",
        module_name="app.result_aggregator.summary_main",
    ),
    ProcessingStage(
        name="Chart Generation",
        module_name="app.visualization.chart_main",
    ),
    ProcessingStage(
        name="HTML Report Generation",
        module_name="app.reporting.html_report_main",
    ),
]


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete CogExPerfAgent performance "
            "collection and reporting pipeline."
        )
    )

    parser.add_argument(
        "--entity",
        required=True,
        help="Entity name from config/entities.yaml",
    )

    parser.add_argument(
        "--start-time",
        required=True,
        type=parse_iso_time,
        help="Collection start time in ISO-8601 format",
    )

    parser.add_argument(
        "--end-time",
        required=True,
        type=parse_iso_time,
        help="Collection end time in ISO-8601 format",
    )

    parser.add_argument(
        "--interval",
        default=None,
        help="Histogram interval, for example 30s or 1m",
    )

    parser.add_argument(
        "--component",
        default=None,
        help=(
            "Optional component name. "
            "By default, all enabled components are processed."
        ),
    )

    parser.add_argument(
        "--execution-id",
        default=None,
        help=(
            "Optional custom execution ID. "
            "By default, one is generated automatically."
        ),
    )

    return parser


def run_processing_stage(
    stage: ProcessingStage,
    execution_id: str,
    entity_name: str,
) -> None:
    """
    Execute one post-collection processing stage.

    The same Python interpreter/virtual environment used
    for app.main is used for every stage.
    """

    command = [
        sys.executable,
        "-m",
        stage.module_name,
        "--execution-id",
        execution_id,
        "--entity",
        entity_name,
    ]

    print()
    print("=" * 70)
    print(f"Starting: {stage.name}")
    print("=" * 70)

    try:
        completed_process = subprocess.run(
            command,
            check=False,
        )

    except OSError as exc:
        raise OrchestratorError(
            f"Could not start stage "
            f"'{stage.name}': {exc}"
        ) from exc

    if completed_process.returncode != 0:
        raise OrchestratorError(
            f"Stage '{stage.name}' failed "
            f"with exit code "
            f"{completed_process.returncode}."
        )

    print()
    print(f"Completed: {stage.name}")


def get_output_directory() -> Path:
    """
    Read the configured output directory so the final
    report location can be displayed correctly.
    """

    config_loader = ConfigLoader()

    application_config = (
        config_loader.load_application_config()
    )

    collection_config = application_config.get(
        "collection",
        {},
    )

    if not isinstance(collection_config, dict):
        return Path("output")

    return Path(
        str(
            collection_config.get(
                "output_directory",
                "output",
            )
        )
    )


def main() -> None:
    args = build_argument_parser().parse_args()

    print()
    print("=" * 70)
    print("CogExPerfAgent")
    print("=" * 70)
    print(f"Entity     : {args.entity}")
    print(f"Start Time : {args.start_time}")
    print(f"End Time   : {args.end_time}")

    if args.interval:
        print(f"Interval   : {args.interval}")

    if args.component:
        print(f"Component  : {args.component}")

    try:
        # -------------------------------------------------
        # Stage 1 - Elasticsearch collection
        # -------------------------------------------------

        print()
        print("=" * 70)
        print("Starting: Result Collection")
        print("=" * 70)

        execution_id = run_collection(
            entity_name=args.entity,
            start_time=args.start_time,
            end_time=args.end_time,
            component=args.component,
            interval=args.interval,
            execution_id=args.execution_id,
        )

        print()
        print("Completed: Result Collection")
        print(f"Execution ID: {execution_id}")

        # -------------------------------------------------
        # Remaining processing stages
        # -------------------------------------------------

        for stage in PROCESSING_STAGES:
            run_processing_stage(
                stage=stage,
                execution_id=execution_id,
                entity_name=args.entity,
            )

        # -------------------------------------------------
        # Final report
        # -------------------------------------------------

        output_directory = get_output_directory()

        report_file = (
            output_directory
            / execution_id
            / "reports"
            / args.entity
            / f"{execution_id}_PSR_Report.html"
        )

        print()
        print("=" * 70)
        print("CogExPerfAgent execution completed")
        print("=" * 70)
        print(f"Execution ID : {execution_id}")
        print(f"Entity       : {args.entity}")
        print(f"Report       : {report_file}")
        print()
        print(
            "Performance PASS/FAIL result is available "
            "inside the PSR report."
        )

    except (
        ConfigurationError,
        ElasticClientError,
        CollectorError,
        JsonWriterError,
        OrchestratorError,
    ) as exc:
        print()
        print("=" * 70)
        print("CogExPerfAgent execution failed")
        print("=" * 70)
        print(f"Error: {exc}")

        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()