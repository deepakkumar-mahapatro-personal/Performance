from typing import Any

from app.elastic_client import ElasticClient
from app.result_collector.base import (
    BaseCollector,
    CollectorError,
)
from app.result_collector.kubernetes_collector import (
    KubernetesCollector,
)


COLLECTOR_REGISTRY: dict[str, type[BaseCollector]] = {
    "kubernetes": KubernetesCollector,
}


def create_collector(
    collector_type: str,
    elastic_client: ElasticClient,
    collector_config: dict[str, Any],
) -> BaseCollector:
    """
    Create the requested collector using the registry.
    """

    normalized_type = collector_type.strip().lower()

    collector_class = COLLECTOR_REGISTRY.get(
        normalized_type
    )

    if collector_class is None:
        available_collectors = ", ".join(
            sorted(COLLECTOR_REGISTRY)
        )

        raise CollectorError(
            f"Unsupported collector type '{collector_type}'. "
            f"Available collectors: {available_collectors}"
        )

    return collector_class(
        elastic_client=elastic_client,
        collector_config=collector_config,
    )