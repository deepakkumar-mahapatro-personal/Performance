import argparse
from typing import Any

from app.config_loader import (
    ConfigLoader,
    ConfigurationError,
)
from app.readers.raw_reader import (
    RawResultReader,
    RawResultReaderError,
)
from app.result_aggregator.normalizer import (
    KubernetesResultNormalizer,
    NormalizationError,
)
from app.writers.csv_writer import (
    CsvWriter,
    CsvWriterError,
)
from app.writers.json_writer import (
    JsonWriter,
    JsonWriterError,
)


NORMALIZER_REGISTRY = {
    "kubernetes": KubernetesResultNormalizer,
}


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize raw performance results and "
            "generate time-series tables."
        )
    )

    parser.add_argument(
        "--execution-id",
        required=True,
        help="Execution folder name under output/",
    )

    parser.add_argument(
        "--entity",
        required=True,
        help="Entity name used during collection",
    )

    parser.add_argument(
        "--component",
        required=False,
        help="Process only one component",
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
        raise ConfigurationError(
            "'collection' configuration must be "
            "a dictionary in application.yaml."
        )

    return str(
        collection_config.get(
            "output_directory",
            "output",
        )
    )


def main() -> None:
    args = build_argument_parser().parse_args()

    try:
        config_loader = ConfigLoader()

        application_config = (
            config_loader.load_application_config()
        )

        collector_types = (
            config_loader.load_collector_types()
        )

        output_directory = get_output_directory(
            application_config
        )

        raw_reader = RawResultReader(
            output_directory=output_directory
        )

        json_writer = JsonWriter(
            output_directory=output_directory
        )

        csv_writer = CsvWriter(
            output_directory=output_directory
        )

        raw_files = raw_reader.find_component_files(
            execution_id=args.execution_id,
            entity_name=args.entity,
            component_name=args.component,
        )

        successful_components: list[str] = []
        failed_components: list[str] = []

        for raw_file in raw_files:
            component_name = raw_file.parent.name

            try:
                raw_result = raw_reader.read(raw_file)

                metadata = raw_result.get(
                    "metadata",
                    {},
                )

                if not isinstance(metadata, dict):
                    raise NormalizationError(
                        f"Metadata is invalid in {raw_file}"
                    )

                component_name = metadata.get(
                    "component_name",
                    component_name,
                )

                collector_type = metadata.get(
                    "collector_type"
                )

                if not isinstance(
                    collector_type,
                    str,
                ) or not collector_type:
                    raise NormalizationError(
                        f"Collector type is missing in "
                        f"{raw_file}"
                    )

                normalizer_class = (
                    NORMALIZER_REGISTRY.get(
                        collector_type
                    )
                )

                if normalizer_class is None:
                    raise NormalizationError(
                        f"No normalizer is registered for "
                        f"collector type '{collector_type}'."
                    )

                collector_config = (
                    collector_types.get(
                        collector_type
                    )
                )

                if not isinstance(
                    collector_config,
                    dict,
                ):
                    raise NormalizationError(
                        f"Collector configuration "
                        f"'{collector_type}' was not found."
                    )

                print(
                    f"Normalizing component: "
                    f"{component_name}"
                )

                normalizer = normalizer_class(
                    collector_config=collector_config
                )

                normalized_result = normalizer.normalize(
                    raw_result=raw_result,
                    execution_id=args.execution_id,
                    entity_name=args.entity,
                )

                json_file = (
                    json_writer.write_timeseries_result(
                        execution_id=args.execution_id,
                        entity_name=args.entity,
                        component_name=component_name,
                        result=normalized_result,
                    )
                )

                long_csv_file = (
                    csv_writer.write_long_timeseries(
                        execution_id=args.execution_id,
                        entity_name=args.entity,
                        component_name=component_name,
                        normalized_result=normalized_result,
                    )
                )

                wide_csv_file = (
                    csv_writer.write_wide_timeseries(
                        execution_id=args.execution_id,
                        entity_name=args.entity,
                        component_name=component_name,
                        normalized_result=normalized_result,
                    )
                )

                record_count = (
                    normalized_result
                    .get("metadata", {})
                    .get("record_count", 0)
                )

                print(
                    f"Completed: {component_name}"
                )
                print(
                    f"Normalized records: {record_count}"
                )
                print(
                    f"JSON: {json_file}"
                )
                print(
                    f"Long CSV: {long_csv_file}"
                )
                print(
                    f"Wide CSV: {wide_csv_file}"
                )

                successful_components.append(
                    component_name
                )

            except (
                RawResultReaderError,
                NormalizationError,
                JsonWriterError,
                CsvWriterError,
            ) as exc:
                print(
                    f"Failed: {component_name} - {exc}"
                )

                failed_components.append(
                    component_name
                )

        print()
        print("Normalization summary")
        print("---------------------")
        print(
            f"Successful: "
            f"{len(successful_components)}"
        )
        print(
            f"Failed    : "
            f"{len(failed_components)}"
        )

        if failed_components:
            print(
                "Failed components: "
                + ", ".join(failed_components)
            )

            raise SystemExit(1)

    except (
        ConfigurationError,
        RawResultReaderError,
        NormalizationError,
        JsonWriterError,
        CsvWriterError,
    ) as exc:
        print(f"Normalization error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()