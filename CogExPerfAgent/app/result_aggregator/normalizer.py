import math
from datetime import datetime, timezone
from typing import Any


class NormalizationError(Exception):
    """Raised when raw Elasticsearch data cannot be normalized."""


class KubernetesResultNormalizer:
    """
    Converts a nested Elasticsearch Kubernetes aggregation response
    into flat, long-format records.

    Each normalized record represents:

        one execution
        + one entity
        + one component
        + one container/pod
        + one timestamp
        + one metric

    Elasticsearch field names such as:

        kubernetes.container.name
        kubernetes.pod.name

    are preserved as-is in the normalized output.
    """

    def __init__(
        self,
        collector_config: dict[str, Any],
    ) -> None:
        if not isinstance(collector_config, dict):
            raise NormalizationError(
                "Kubernetes collector configuration "
                "must be a dictionary."
            )

        self.collector_config = collector_config

    def normalize(
        self,
        raw_result: dict[str, Any],
        execution_id: str,
        entity_name: str,
    ) -> dict[str, Any]:
        """
        Normalize one component's raw Elasticsearch response.

        Args:
            raw_result:
                Raw JSON result created by the Result Collector.

            execution_id:
                Execution folder name.

            entity_name:
                Entity being analyzed, for example item-ingestion.

        Returns:
            A dictionary containing metadata, column definitions
            and normalized long-format records.
        """

        if not isinstance(raw_result, dict):
            raise NormalizationError(
                "Raw result must be a dictionary."
            )

        if not execution_id:
            raise NormalizationError(
                "Execution ID cannot be empty."
            )

        if not entity_name:
            raise NormalizationError(
                "Entity name cannot be empty."
            )

        metadata = raw_result.get("metadata")

        if not isinstance(metadata, dict):
            raise NormalizationError(
                "Raw result metadata is missing or invalid."
            )

        component_name = metadata.get("component_name")
        collector_type = metadata.get("collector_type")

        if not isinstance(component_name, str) or not component_name:
            raise NormalizationError(
                "Component name is missing from raw metadata."
            )

        if not isinstance(collector_type, str) or not collector_type:
            raise NormalizationError(
                "Collector type is missing from raw metadata."
            )

        elasticsearch_response = raw_result.get(
            "elasticsearch_response"
        )

        if not isinstance(elasticsearch_response, dict):
            raise NormalizationError(
                "Elasticsearch response is missing or invalid."
            )

        pod_buckets = (
            elasticsearch_response
            .get("aggregations", {})
            .get("pods", {})
            .get("buckets", [])
        )

        if not isinstance(pod_buckets, list):
            raise NormalizationError(
                "Expected aggregations.pods.buckets to be a list."
            )

        metric_configs = self._get_metric_configs()
        group_fields = self._get_group_fields()

        records: list[dict[str, Any]] = []

        for pod_bucket in pod_buckets:
            if not isinstance(pod_bucket, dict):
                continue

            group_values = self._build_group_values(
                group_key=pod_bucket.get("key"),
                group_fields=group_fields,
            )

            time_buckets = (
                pod_bucket
                .get("every_30s", {})
                .get("buckets", [])
            )

            if not isinstance(time_buckets, list):
                continue

            for time_bucket in time_buckets:
                if not isinstance(time_bucket, dict):
                    continue

                timestamp = (
                    time_bucket.get("key_as_string")
                    or time_bucket.get("key")
                )

                timestamp_epoch_ms = time_bucket.get("key")

                document_count = self._safe_integer(
                    time_bucket.get("doc_count", 0)
                )

                for metric_name, metric_config in (
                    metric_configs.items()
                ):
                    metric_result = time_bucket.get(
                        metric_name,
                        {},
                    )

                    raw_value = None

                    if isinstance(metric_result, dict):
                        raw_value = metric_result.get("value")

                    scale_factor = self._get_scale_factor(
                        metric_name=metric_name,
                        metric_config=metric_config,
                    )

                    scaled_value = self._scale_value(
                        raw_value=raw_value,
                        scale_factor=scale_factor,
                    )

                    record: dict[str, Any] = {
                        "execution_id": execution_id,
                        "entity_name": entity_name,
                        "component_name": component_name,
                        "component_display_name": metadata.get(
                            "display_name",
                            component_name,
                        ),
                        "collector_type": collector_type,
                        "timestamp": timestamp,
                        "timestamp_epoch_ms": timestamp_epoch_ms,
                        "document_count": document_count,

                        # Preserves these exact Elasticsearch field names:
                        #
                        # kubernetes.container.name
                        # kubernetes.pod.name
                        **group_values,

                        "metric_name": metric_name,
                        "metric_display_name": metric_config.get(
                            "display_name",
                            metric_name,
                        ),
                        "raw_value": (
                            float(raw_value)
                            if self._is_number(raw_value)
                            else None
                        ),
                        "value": scaled_value,
                        "unit": metric_config.get("unit"),
                        "scale_factor": scale_factor,
                        "has_data": scaled_value is not None,
                    }

                    records.append(record)

        return {
            "metadata": {
                "execution_id": execution_id,
                "entity_name": entity_name,
                "component_name": component_name,
                "component_display_name": metadata.get(
                    "display_name",
                    component_name,
                ),
                "collector_type": collector_type,
                "index": metadata.get("index"),
                "start_time": metadata.get("start_time"),
                "end_time": metadata.get("end_time"),
                "interval": metadata.get("interval"),
                "normalized_at": (
                    datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                ),
                "group_count": len(pod_buckets),
                "record_count": len(records),
                "metric_names": list(metric_configs.keys()),
                "group_fields": group_fields,
            },
            "columns": self._build_column_list(
                group_fields=group_fields
            ),
            "records": records,
        }

    def _get_metric_configs(
        self,
    ) -> dict[str, dict[str, Any]]:
        """
        Return all enabled metric definitions from collector_types.yaml.
        """

        metrics = self.collector_config.get(
            "metrics",
            {},
        )

        if not isinstance(metrics, dict) or not metrics:
            raise NormalizationError(
                "No Kubernetes metrics are configured."
            )

        enabled_metrics: dict[str, dict[str, Any]] = {}

        for metric_name, metric_config in metrics.items():
            if not isinstance(metric_config, dict):
                raise NormalizationError(
                    f"Metric '{metric_name}' must be a dictionary."
                )

            if metric_config.get("enabled", True) is False:
                continue

            enabled_metrics[metric_name] = metric_config

        if not enabled_metrics:
            raise NormalizationError(
                "All Kubernetes metrics are disabled."
            )

        return enabled_metrics

    def _get_group_fields(
        self,
    ) -> list[str]:
        """
        Return grouping fields from collector_types.yaml.

        Example:

            group_by:
              - kubernetes.container.name
              - kubernetes.pod.name
        """

        group_fields = self.collector_config.get(
            "group_by",
            [],
        )

        if not isinstance(group_fields, list) or not group_fields:
            raise NormalizationError(
                "At least one group_by field is required."
            )

        validated_fields: list[str] = []

        for field in group_fields:
            if not isinstance(field, str) or not field:
                raise NormalizationError(
                    "Every group_by value must be "
                    "a non-empty string."
                )

            validated_fields.append(field)

        return validated_fields

    @staticmethod
    def _build_group_values(
        group_key: Any,
        group_fields: list[str],
    ) -> dict[str, Any]:
        """
        Convert the Elasticsearch multi_terms key into field/value pairs.

        Example Elasticsearch key:

            [
                "service",
                "beacon-ingress-service-abc123"
            ]

        Result:

            {
                "kubernetes.container.name": "service",
                "kubernetes.pod.name":
                    "beacon-ingress-service-abc123"
            }
        """

        if isinstance(group_key, list):
            key_values = group_key

        elif len(group_fields) == 1:
            key_values = [group_key]

        else:
            key_values = []

        group_values: dict[str, Any] = {}

        for position, field in enumerate(group_fields):
            if position < len(key_values):
                group_values[field] = key_values[position]
            else:
                group_values[field] = None

        return group_values

    @staticmethod
    def _get_scale_factor(
        metric_name: str,
        metric_config: dict[str, Any],
    ) -> float:
        """
        Read and validate the metric scale factor.

        Examples:

            CPU raw value 0.25 × 100 = 25%
            Memory bytes × 1 = original byte value
        """

        scale_factor = metric_config.get(
            "scale_factor",
            1,
        )

        try:
            return float(scale_factor)

        except (TypeError, ValueError) as exc:
            raise NormalizationError(
                f"Metric '{metric_name}' has invalid "
                f"scale_factor '{scale_factor}'."
            ) from exc

    @staticmethod
    def _scale_value(
        raw_value: Any,
        scale_factor: float,
    ) -> float | None:
        """
        Apply the configured scale factor to a metric value.
        """

        if not KubernetesResultNormalizer._is_number(
            raw_value
        ):
            return None

        return round(
            float(raw_value) * scale_factor,
            6,
        )

    @staticmethod
    def _is_number(
        value: Any,
    ) -> bool:
        """
        Return True only for valid finite numeric values.
        """

        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )

    @staticmethod
    def _safe_integer(
        value: Any,
    ) -> int:
        """
        Safely convert a value into an integer.
        """

        try:
            return int(value)

        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _build_column_list(
        group_fields: list[str],
    ) -> list[str]:
        """
        Define the output column order for JSON and CSV writers.
        """

        return [
            "execution_id",
            "entity_name",
            "component_name",
            "component_display_name",
            "collector_type",
            "timestamp",
            "timestamp_epoch_ms",
            "document_count",
            *group_fields,
            "metric_name",
            "metric_display_name",
            "raw_value",
            "value",
            "unit",
            "scale_factor",
            "has_data",
        ]