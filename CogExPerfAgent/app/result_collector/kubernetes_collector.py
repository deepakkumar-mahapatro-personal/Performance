from typing import Any

from app.elastic_client import ElasticClientError
from app.query_builders.kubernetes_query import (
    KubernetesQueryBuilder,
    QueryBuilderError,
)
from app.result_collector.base import (
    BaseCollector,
    CollectorError,
)


class KubernetesCollector(BaseCollector):
    """
    Collects Kubernetes CPU and memory metrics from Elasticsearch.
    """

    collector_type = "kubernetes"

    def __init__(
        self,
        elastic_client,
        collector_config: dict[str, Any],
    ) -> None:
        super().__init__(
            elastic_client=elastic_client,
            collector_config=collector_config,
        )

        self.query_builder = KubernetesQueryBuilder(
            collector_config=collector_config
        )

    def collect(
        self,
        component_name: str,
        component_config: dict[str, Any],
        start_time: str,
        end_time: str,
        interval: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(component_config, dict):
            raise CollectorError(
                f"Configuration for component "
                f"'{component_name}' must be a dictionary."
            )

        component_filters = component_config.get(
            "filters",
            {},
        )

        if not isinstance(component_filters, dict):
            raise CollectorError(
                f"'filters' for component '{component_name}' "
                f"must be a dictionary."
            )

        index = (
            component_config.get("index")
            or self.collector_config.get("default_index")
        )

        if not isinstance(index, str) or not index:
            raise CollectorError(
                f"No Elasticsearch index is configured "
                f"for component '{component_name}'."
            )

        selected_interval = (
            interval
            or self.collector_config.get("default_interval")
            or "30s"
        )

        try:
            query = self.query_builder.build(
                component_filters=component_filters,
                start_time=start_time,
                end_time=end_time,
                interval=str(selected_interval),
            )

            elasticsearch_response = self.elastic_client.search(
                index=index,
                query=query,
            )

        except QueryBuilderError as exc:
            raise CollectorError(
                f"Could not build query for component "
                f"'{component_name}': {exc}"
            ) from exc

        except ElasticClientError as exc:
            raise CollectorError(
                f"Elasticsearch collection failed for "
                f"component '{component_name}': {exc}"
            ) from exc

        pod_buckets = (
            elasticsearch_response
            .get("aggregations", {})
            .get("pods", {})
            .get("buckets", [])
        )

        return {
            "metadata": {
                "component_name": component_name,
                "display_name": component_config.get(
                    "display_name",
                    component_name,
                ),
                "collector_type": self.collector_type,
                "index": index,
                "start_time": start_time,
                "end_time": end_time,
                "interval": selected_interval,
                "filters": component_filters,
                "pod_container_groups": len(pod_buckets),
            },

            # Retaining the query is useful for debugging and verification.
            "query": query,

            # This is the complete raw Elasticsearch response.
            "elasticsearch_response": elasticsearch_response,
        }