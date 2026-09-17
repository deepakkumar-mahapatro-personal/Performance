from collections import defaultdict
from typing import Any

from app.result_aggregator.statistics import (
    StatisticsCalculator,
    StatisticsError,
)


class SummaryBuilderError(Exception):
    """Raised when summary rows cannot be generated."""


class KubernetesSummaryBuilder:
    """
    Creates:

    1. Pod-level summary rows
    2. Component-level summary rows for entity-summary.csv
    """

    def __init__(
        self,
        collector_config: dict[str, Any],
        summary_config: dict[str, Any],
    ) -> None:
        if not isinstance(collector_config, dict):
            raise SummaryBuilderError(
            "Collector configuration must be a dictionary."
            )

        if not isinstance(summary_config, dict):
            raise SummaryBuilderError(
            "Summary configuration must be a dictionary."
            )

        self.collector_config = collector_config
        self.summary_config = summary_config

    def build_pod_summary_rows(
        self,
        normalized_result: dict[str, Any],
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Generate one readable summary row per:

            container + pod + metric

        Only the required high-level statistics are returned.
        """

        metadata, records = self._validate_result(
            normalized_result
        )

        group_fields = metadata.get(
            "group_fields",
            [],
        )

        if not isinstance(group_fields, list):
            raise SummaryBuilderError(
                "group_fields must be a list."
            )

        # This should return only the metrics selected
        # for summary generation.
        metric_configs = self._get_metric_configs()

        grouped_records: dict[
            tuple[Any, ...],
            list[dict[str, Any]],
        ] = defaultdict(list)

        for record in records:
            if not self._is_valid_record(record):
                continue

            metric_name = record.get("metric_name")

            # Skip metrics that are not required in the summary.
            if metric_name not in metric_configs:
                continue

            group_key = tuple(
                record.get(field)
                for field in group_fields
            )

            complete_key = (
                *group_key,
                metric_name,
            )

            grouped_records[complete_key].append(
                record
            )

        rows: list[dict[str, Any]] = []

        sorted_groups = sorted(
            grouped_records.items(),
            key=lambda item: tuple(
                ""
                if value is None
                else str(value)
                for value in item[0]
            ),
        )

        for complete_key, metric_records in sorted_groups:
            metric_name = str(
                complete_key[-1]
            )

            group_values = complete_key[:-1]

            metric_config = metric_configs[
                metric_name
            ]

            values = [
                float(record["value"])
                for record in metric_records
            ]

            statistics = (
                StatisticsCalculator.summarize(
                    values
                )
            )

            peak_record = max(
                metric_records,
                key=lambda record: float(
                    record["value"]
                ),
            )

            row: dict[str, Any] = {
                "execution_id": metadata.get(
                    "execution_id"
                ),
                "entity_name": metadata.get(
                    "entity_name"
                ),
                "component_name": metadata.get(
                    "component_name"
                ),
            }

            # Add exact configured grouping fields:
            #
            # kubernetes.container.name
            # kubernetes.pod.name
            for position, field in enumerate(
                group_fields
            ):
                row[field] = (
                    group_values[position]
                    if position < len(group_values)
                    else None
                )

            row.update(
                {
                    # Use readable display name from reporting config.
                    # Falls back to cpu_pct / mem_pct.
                    "metric_name": metric_config.get(
                        "display_name",
                        metric_name,
                    ),
                    "average": statistics.get(
                        "average"
                    ),
                    "minimum": statistics.get(
                        "minimum"
                    ),
                    "maximum": statistics.get(
                        "maximum"
                    ),
                    "p90": statistics.get(
                        "p90"
                    ),
                    "p95": statistics.get(
                        "p95"
                    ),
                    "p99": statistics.get(
                        "p99"
                    ),
                    "peak_value": (
                        StatisticsCalculator.round_value(
                            float(
                                peak_record["value"]
                            )
                        )
                    ),
                    "peak_timestamp": (
                        peak_record.get(
                            "timestamp"
                        )
                    ),
                }
            )

            rows.append(row)

        return group_fields, rows

    def build_component_summary_rows(
        self,
        normalized_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Generate one component-level row for every metric.

        These rows are combined across components to create
        entity-summary.csv.
        """

        metadata, records = self._validate_result(
            normalized_result
        )
        replica_count = self._calculate_replica_count(
           records
        )

        metric_configs = self._get_metric_configs()
        rows: list[dict[str, Any]] = []

        for metric_name, metric_config in (
            metric_configs.items()
        ):
            timestamp_values: dict[str, list[float]] = (
                defaultdict(list)
            )

            for record in records:
                if not self._is_valid_record(record):
                    continue

                if record.get("metric_name") != metric_name:
                    continue

                timestamp = record.get("timestamp")

                if timestamp is None:
                    continue

                timestamp_values[str(timestamp)].append(
                    float(record["value"])
                )

            component_aggregation = str(
                metric_config.get(
                    "component_aggregation",
                    "avg",
                )
            ).lower()

            component_points: list[dict[str, Any]] = []

            try:
                for timestamp in sorted(timestamp_values):
                    combined_value = (
                        StatisticsCalculator.combine(
                            values=timestamp_values[timestamp],
                            method=component_aggregation,
                        )
                    )

                    if combined_value is None:
                        continue

                    component_points.append(
                        {
                            "timestamp": timestamp,
                            "value": combined_value,
                        }
                    )

            except StatisticsError as exc:
                raise SummaryBuilderError(
                    f"Could not aggregate metric "
                    f"'{metric_name}': {exc}"
                ) from exc

            component_values = [
                float(point["value"])
                for point in component_points
            ]

            statistics = StatisticsCalculator.summarize(
                component_values
            )

            peak_point = (
                max(
                    component_points,
                    key=lambda point: point["value"],
                )
                if component_points
                else None
            )

            lowest_point = (
                min(
                    component_points,
                    key=lambda point: point["value"],
                )
                if component_points
                else None
            )

            rows.append(
                {
                    "execution_id": metadata.get("execution_id"),
                    "entity_name": metadata.get("entity_name"),
                    "component_name": metadata.get("component_name"),
                    "replica_count": replica_count,
                    "metric_name": metric_config.get(
                        "display_name",
                        metric_name,
                    ),
                    "average": statistics.get("average"),
                    "minimum": statistics.get("minimum"),
                    "maximum": statistics.get("maximum"),
                    "p90": statistics.get("p90"),
                    "p95": statistics.get("p95"),
                    "p99": statistics.get("p99"),
                    "peak_value": (
                        peak_point["value"]
                        if peak_point
                        else None
                    ),
                    "peak_timestamp": (
                        peak_point["timestamp"]
                        if peak_point
                        else None
                    ),
                }
            )

        return rows

    def _get_metric_configs(
    self,
    ) -> dict[str, dict[str, Any]]:
        """
        Return only metrics enabled in reporting.yaml.

        Metric field, unit and scale information still comes from
        collector_types.yaml.
        """

        collector_metrics = self.collector_config.get(
        "metrics",
        {},
        )

        reporting_metrics = self.summary_config.get(
        "metrics",
        {},
        )

        if not isinstance(collector_metrics, dict):
            raise SummaryBuilderError(
            "Collector metrics configuration is invalid."
            )

        if not isinstance(reporting_metrics, dict):
            raise SummaryBuilderError(
            "Reporting metrics configuration is invalid."
            )

        selected_metrics: dict[str, dict[str, Any]] = {}

        for metric_name, reporting_metric in reporting_metrics.items():
            if not isinstance(reporting_metric, dict):
                continue

            if reporting_metric.get("enabled", False) is not True:
                continue

            collector_metric = collector_metrics.get(metric_name)

            if not isinstance(collector_metric, dict):
                raise SummaryBuilderError(
                    f"Summary metric '{metric_name}' is not defined "
                    f"in collector_types.yaml."
                )

            selected_metrics[metric_name] = {
                **collector_metric,
                "display_name": reporting_metric.get(
                    "display_name",
                    metric_name,
                ),
                "component_aggregation": reporting_metric.get(
                    "component_aggregation",
                    "avg",
                ),
            }

        if not selected_metrics:
            raise SummaryBuilderError(
                "No metrics are enabled under "
                "reporting.summaries.metrics."
            )

        return selected_metrics

    @staticmethod
    def _validate_result(
        normalized_result: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        if not isinstance(normalized_result, dict):
            raise SummaryBuilderError(
                "Normalized result must be a dictionary."
            )

        metadata = normalized_result.get("metadata")
        records = normalized_result.get("records")

        if not isinstance(metadata, dict):
            raise SummaryBuilderError(
                "Normalized metadata is missing or invalid."
            )

        if not isinstance(records, list):
            raise SummaryBuilderError(
                "Normalized records are missing or invalid."
            )

        return metadata, records
    @staticmethod
    def _calculate_replica_count(
        records: list[dict[str, Any]],
    ) -> int:
        """
        Calculate the maximum number of pods observed
        simultaneously during the execution window.
        """

        pods_by_timestamp: dict[str, set[str]] = defaultdict(set)

        for record in records:
            if not isinstance(record, dict):
                continue

            timestamp = record.get("timestamp")
            pod_name = record.get("kubernetes.pod.name")

            if timestamp is None or not pod_name:
                continue

            pods_by_timestamp[str(timestamp)].add(
                str(pod_name)
            )

        return max(
            (
                len(pod_names)
                for pod_names in pods_by_timestamp.values()
            ),
            default=0,
        )
    @staticmethod
    def _is_valid_record(
        record: Any,
    ) -> bool:
        return (
            isinstance(record, dict)
            and record.get("has_data") is True
            and StatisticsCalculator.is_number(
                record.get("value")
            )
        )