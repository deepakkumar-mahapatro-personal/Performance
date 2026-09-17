import argparse
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

from app.config_loader import (
    ConfigLoader,
    ConfigurationError,
)
from app.elastic_client import (
    ElasticClient,
    ElasticClientError,
)
from app.registry import create_collector
from app.result_collector.base import CollectorError
from app.writers.json_writer import (
    JsonWriter,
    JsonWriterError,
)


def parse_iso_time(value: str) -> str:
    """
    Validate that a command-line value is an ISO-8601 timestamp.
    """

    try:
        parsed_time = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid ISO-8601 timestamp: {value}"
        ) from exc

    if parsed_time.tzinfo is None:
        raise argparse.ArgumentTypeError(
            f"Timestamp must contain a timezone: {value}"
        )

    return value


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Collect performance metrics for a configured entity."
        )
    )

    parser.add_argument(
        "--entity",
        required=True,
        help="Entity name from config/entities.yaml",
    )

    parser.add_argument(
        "--component",
        required=False,
        help=(
            "Collect one component only. "
            "By default, all enabled components are collected."
        ),
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
        "--execution-id",
        default=None,
        help="Optional custom execution ID",
    )

    return parser


def generate_execution_id(
    entity_name: str,
) -> str:
    current_time = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    return f"{entity_name}-{current_time}"


def validate_time_range(
    start_time: str,
    end_time: str,
) -> None:
    parsed_start = datetime.fromisoformat(
        start_time.replace("Z", "+00:00")
    )

    parsed_end = datetime.fromisoformat(
        end_time.replace("Z", "+00:00")
    )

    if parsed_start >= parsed_end:
        raise ConfigurationError(
            "Start time must be earlier than end time."
        )


def get_entity_components(
    entities: dict[str, Any],
    component_definitions: dict[str, Any],
    entity_name: str,
    selected_component: str | None,
) -> dict[str, Any]:
    """
    Resolve component names configured for an entity
    to their full component definitions.
    """

    entity_components = entities.get(entity_name)

    if not isinstance(entity_components, list):
        available_entities = ", ".join(
            sorted(entities)
        )

        raise ConfigurationError(
            f"Entity '{entity_name}' was not found or "
            f"does not contain a valid component list. "
            f"Available entities: {available_entities}"
        )

    if not entity_components:
        raise ConfigurationError(
            f"Entity '{entity_name}' has no components."
        )

    for component_name in entity_components:
        if not isinstance(component_name, str) or not component_name:
            raise ConfigurationError(
                f"Entity '{entity_name}' contains an "
                f"invalid component name."
            )

    if selected_component:
        if selected_component not in entity_components:
            available_components = ", ".join(
                entity_components
            )

            raise ConfigurationError(
                f"Component '{selected_component}' is not "
                f"configured for entity '{entity_name}'. "
                f"Available components: {available_components}"
            )

        component_names = [
            selected_component
        ]

    else:
        component_names = entity_components

    resolved_components: dict[str, Any] = {}

    for component_name in component_names:
        component_config = component_definitions.get(
            component_name
        )

        if not isinstance(component_config, dict):
            raise ConfigurationError(
                f"Component '{component_name}' used by "
                f"entity '{entity_name}' was not found "
                f"in components.yaml."
            )

        resolved_components[
            component_name
        ] = component_config

    return resolved_components


def run_collection(
    entity_name: str,
    start_time: str,
    end_time: str,
    component: str | None = None,
    interval: str | None = None,
    execution_id: str | None = None,
) -> str:
    """
    Run Elasticsearch collection for an entity.

    Returns:
        execution_id generated or supplied for this execution.
    """

    load_dotenv()

    validate_time_range(
        start_time=start_time,
        end_time=end_time,
    )

    config_loader = ConfigLoader()

    application_config = (
        config_loader.load_application_config()
    )

    collector_types = (
        config_loader.load_collector_types()
    )
    component_definitions = (
        config_loader.load_components()
    )
    entities = config_loader.load_entities()

    elastic_config = application_config.get("elastic")

    if not isinstance(elastic_config, dict):
        raise ConfigurationError(
            "'elastic' configuration is missing "
            "from application.yaml."
        )

    collection_config = application_config.get(
        "collection",
        {},
    )

    if not isinstance(collection_config, dict):
        raise ConfigurationError(
            "'collection' configuration must be a dictionary."
        )

    output_directory = collection_config.get(
        "output_directory",
        "output",
    )

    execution_id = (
        execution_id
        or generate_execution_id(entity_name)
    )

    components = get_entity_components(
        entities=entities,
        component_definitions=component_definitions,
        entity_name=entity_name,
        selected_component=component,
    )

    json_writer = JsonWriter(
        output_directory=str(output_directory)
    )

    successful_components: list[str] = []
    failed_components: list[str] = []

    collector_instances = {}

    with ElasticClient.from_config(
        elastic_config
    ) as elastic_client:

        for component_name, component_config in (
            components.items()
        ):
            if component_config.get(
                "enabled",
                True,
            ) is False:
                print(
                    f"Skipped disabled component: "
                    f"{component_name}"
                )
                continue

            collector_type = component_config.get(
                "collector_type"
            )

            if not isinstance(
                collector_type,
                str,
            ) or not collector_type:
                print(
                    f"Failed: {component_name} - "
                    f"collector_type is missing"
                )

                failed_components.append(
                    component_name
                )
                continue

            collector_config = collector_types.get(
                collector_type
            )

            if not isinstance(
                collector_config,
                dict,
            ):
                print(
                    f"Failed: {component_name} - "
                    f"collector configuration "
                    f"'{collector_type}' was not found"
                )

                failed_components.append(
                    component_name
                )
                continue

            try:
                if collector_type not in collector_instances:
                    collector_instances[collector_type] = (
                        create_collector(
                            collector_type=collector_type,
                            elastic_client=elastic_client,
                            collector_config=collector_config,
                        )
                    )

                collector = collector_instances[
                    collector_type
                ]

                print(
                    f"Collecting component: "
                    f"{component_name}"
                )

                result = collector.collect(
                    component_name=component_name,
                    component_config=component_config,
                    start_time=start_time,
                    end_time=end_time,
                    interval=interval,
                )

                output_file = (
                    json_writer.write_raw_result(
                        execution_id=execution_id,
                        entity_name=entity_name,
                        component_name=component_name,
                        collector_type=collector_type,
                        result=result,
                    )
                )

                group_count = (
                    result
                    .get("metadata", {})
                    .get("pod_container_groups", 0)
                )

                print(
                    f"Completed: {component_name}"
                )
                print(
                    f"Groups returned: {group_count}"
                )
                print(
                    f"Output: {output_file}"
                )

                successful_components.append(
                    component_name
                )

            except (
                CollectorError,
                JsonWriterError,
            ) as exc:
                print(
                    f"Failed: {component_name} - {exc}"
                )

                failed_components.append(
                    component_name
                )

    print()
    print("Collection summary")
    print("------------------")
    print(f"Execution ID : {execution_id}")
    print(
        f"Successful   : "
        f"{len(successful_components)}"
    )
    print(
        f"Failed       : "
        f"{len(failed_components)}"
    )

    if failed_components:
        print(
            "Failed components: "
            + ", ".join(failed_components)
        )

        raise CollectorError(
            "Collection failed for component(s): "
            + ", ".join(failed_components)
        )

    return execution_id


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    try:
        run_collection(
            entity_name=args.entity,
            start_time=args.start_time,
            end_time=args.end_time,
            component=args.component,
            interval=args.interval,
            execution_id=args.execution_id,
        )

    except (
        ConfigurationError,
        ElasticClientError,
        CollectorError,
        JsonWriterError,
    ) as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()