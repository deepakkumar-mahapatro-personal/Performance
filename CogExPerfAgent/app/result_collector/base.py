from abc import ABC, abstractmethod
from typing import Any

from app.elastic_client import ElasticClient


class CollectorError(Exception):
    """Raised when a result collector cannot collect data."""


class BaseCollector(ABC):
    """
    Base interface for all collectors.

    Future collectors such as transaction, SQL and Kafka
    will implement this same interface.
    """

    collector_type: str

    def __init__(
        self,
        elastic_client: ElasticClient,
        collector_config: dict[str, Any],
    ) -> None:
        if not isinstance(collector_config, dict):
            raise CollectorError(
                "Collector configuration must be a dictionary."
            )

        self.elastic_client = elastic_client
        self.collector_config = collector_config

    @abstractmethod
    def collect(
        self,
        component_name: str,
        component_config: dict[str, Any],
        start_time: str,
        end_time: str,
        interval: str | None = None,
    ) -> dict[str, Any]:
        """Collect data for one component."""