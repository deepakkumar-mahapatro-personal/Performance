from typing import Any


class QueryBuilderError(Exception):
    """Raised when a Kubernetes Elasticsearch query cannot be built."""


class KubernetesQueryBuilder:
    """
    Builds Kubernetes CPU and memory aggregation queries.

    Query structure and field mappings come from collector_types.yaml.
    Component-specific values come from entities.yaml.
    """

    SUPPORTED_AGGREGATIONS = {
        "avg",
        "min",
        "max",
        "sum",
        "value_count",
        "cardinality",
    }

    def __init__(
        self,
        collector_config: dict[str, Any],
    ) -> None:
        if not isinstance(collector_config, dict):
            raise QueryBuilderError(
                "Kubernetes collector configuration must be a dictionary."
            )

        self.collector_config = collector_config

    def build(
        self,
        component_filters: dict[str, Any],
        start_time: str,
        end_time: str,
        interval: str | None = None,
    ) -> dict[str, Any]:
        """
        Build the validated common Kubernetes query.

        Args:
            component_filters:
                Project, resource and container values from entities.yaml.

            start_time:
                Test start time in ISO-8601 format.

            end_time:
                Test end time in ISO-8601 format.

            interval:
                Histogram interval, such as 30s or 1m.
        """

        self._validate_runtime_values(
            component_filters=component_filters,
            start_time=start_time,
            end_time=end_time,
        )

        timestamp_field = str(
            self.collector_config.get(
                "timestamp_field",
                "@timestamp",
            )
        )

        selected_interval = (
            interval
            or self.collector_config.get("default_interval")
            or "30s"
        )

        filter_values = self._merge_filter_values(
            component_filters
        )

        filters = self._build_base_filters(
            filter_values
        )

        # Keep the validated query behavior:
        # start time is inclusive and end time is exclusive.
        filters.append(
            {
                "range": {
                    timestamp_field: {
                        "gte": start_time,
                        "lt": end_time,
                    }
                }
            }
        )

        filters.extend(
            self._build_optional_filters(
                filter_values
            )
        )

        bool_query: dict[str, Any] = {
            "filter": filters,
        }

        exclusions = self._build_exclusions()

        if exclusions:
            bool_query["must_not"] = exclusions

        return {
            "size": 0,
            "query": {
                "bool": bool_query,
            },
            "aggs": {
                "pods": {
                    "multi_terms": {
                        "terms": self._build_group_fields(),
                        "size": int(
                            self.collector_config.get(
                                "group_size",
                                100,
                            )
                        ),
                    },
                    "aggs": {
                        "every_30s": {
                            "date_histogram": {
                                "field": timestamp_field,
                                "fixed_interval": selected_interval,
                                "time_zone": "UTC",
                                "min_doc_count": 0,
                            },
                            "aggs": (
                                self._build_metric_aggregations()
                            ),
                        }
                    },
                }
            },
        }

    def _merge_filter_values(
        self,
        component_filters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Merge shared default values with component-specific values.

        Component values override defaults.
        """

        default_values = self.collector_config.get(
            "default_filter_values",
            {},
        )

        if not isinstance(default_values, dict):
            raise QueryBuilderError(
                "'default_filter_values' must be a dictionary."
            )

        merged_values = dict(default_values)
        merged_values.update(component_filters)

        return merged_values

    def _build_base_filters(
        self,
        filter_values: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build project, stage, geography and dataset filters.
        """

        base_filter_names = self.collector_config.get(
            "base_filters",
            [],
        )

        if not isinstance(base_filter_names, list):
            raise QueryBuilderError(
                "'base_filters' must be a list."
            )

        filters: list[dict[str, Any]] = []

        for filter_name in base_filter_names:
            value = filter_values.get(filter_name)

            if value is None or value == "":
                raise QueryBuilderError(
                    f"Required filter '{filter_name}' is missing."
                )

            field = self._get_filter_field(filter_name)

            filters.append(
                {
                    "term": {
                        field: value,
                    }
                }
            )

        return filters

    def _build_optional_filters(
        self,
        filter_values: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build resource and container filters when values exist.
        """

        optional_filter_names = self.collector_config.get(
            "optional_filters",
            [],
        )

        if not isinstance(optional_filter_names, list):
            raise QueryBuilderError(
                "'optional_filters' must be a list."
            )

        filters: list[dict[str, Any]] = []

        for filter_name in optional_filter_names:
            value = filter_values.get(filter_name)

            if value is None or value == "":
                continue

            field = self._get_filter_field(filter_name)

            filters.append(
                {
                    "term": {
                        field: value,
                    }
                }
            )

        return filters

    def _get_filter_field(
        self,
        filter_name: str,
    ) -> str:
        field_mappings = self.collector_config.get(
            "filter_fields",
            {},
        )

        if not isinstance(field_mappings, dict):
            raise QueryBuilderError(
                "'filter_fields' must be a dictionary."
            )

        field = field_mappings.get(filter_name)

        if not isinstance(field, str) or not field:
            raise QueryBuilderError(
                f"No Elasticsearch field is configured "
                f"for filter '{filter_name}'."
            )

        return field

    def _build_exclusions(
        self,
    ) -> list[dict[str, Any]]:
        exclusions = self.collector_config.get(
            "exclusions",
            {},
        )

        if not exclusions:
            return []

        if not isinstance(exclusions, dict):
            raise QueryBuilderError(
                "'exclusions' must be a dictionary."
            )

        field = exclusions.get("field")
        values = exclusions.get("values", [])

        if not field or not values:
            return []

        if not isinstance(field, str):
            raise QueryBuilderError(
                "Exclusion field must be a string."
            )

        if not isinstance(values, list):
            raise QueryBuilderError(
                "Exclusion values must be a list."
            )

        return [
            {
                "terms": {
                    field: values,
                }
            }
        ]

    def _build_group_fields(
        self,
    ) -> list[dict[str, str]]:
        group_fields = self.collector_config.get(
            "group_by",
            [],
        )

        if not isinstance(group_fields, list) or not group_fields:
            raise QueryBuilderError(
                "At least one 'group_by' field is required."
            )

        terms: list[dict[str, str]] = []

        for field in group_fields:
            if not isinstance(field, str) or not field:
                raise QueryBuilderError(
                    "Every group field must be a non-empty string."
                )

            terms.append(
                {
                    "field": field,
                }
            )

        return terms

    def _build_metric_aggregations(
        self,
    ) -> dict[str, Any]:
        metrics = self.collector_config.get(
            "metrics",
            {},
        )

        if not isinstance(metrics, dict) or not metrics:
            raise QueryBuilderError(
                "No Kubernetes metrics are configured."
            )

        aggregations: dict[str, Any] = {}

        for metric_name, metric_config in metrics.items():
            if not isinstance(metric_config, dict):
                raise QueryBuilderError(
                    f"Metric '{metric_name}' must be a dictionary."
                )

            if metric_config.get("enabled", True) is False:
                continue

            field = metric_config.get("field")
            aggregation = str(
                metric_config.get(
                    "aggregation",
                    "avg",
                )
            ).lower()

            if not isinstance(field, str) or not field:
                raise QueryBuilderError(
                    f"Metric '{metric_name}' has no field."
                )

            if aggregation not in self.SUPPORTED_AGGREGATIONS:
                raise QueryBuilderError(
                    f"Unsupported aggregation '{aggregation}' "
                    f"for metric '{metric_name}'."
                )

            aggregations[metric_name] = {
                aggregation: {
                    "field": field,
                }
            }

        if not aggregations:
            raise QueryBuilderError(
                "All Kubernetes metrics are disabled."
            )

        return aggregations

    @staticmethod
    def _validate_runtime_values(
        component_filters: dict[str, Any],
        start_time: str,
        end_time: str,
    ) -> None:
        if not isinstance(component_filters, dict):
            raise QueryBuilderError(
                "Component filters must be a dictionary."
            )

        if not isinstance(start_time, str) or not start_time:
            raise QueryBuilderError(
                "Start time must be provided."
            )

        if not isinstance(end_time, str) or not end_time:
            raise QueryBuilderError(
                "End time must be provided."
            )