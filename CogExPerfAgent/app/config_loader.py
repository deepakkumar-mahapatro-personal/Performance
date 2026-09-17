from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(Exception):
    """Raised when application configuration is missing or invalid."""


class ConfigLoader:
    def __init__(self, config_directory: str = "config") -> None:
        self.config_directory = Path(config_directory)

        if not self.config_directory.exists():
            raise ConfigurationError(
                f"Configuration directory does not exist: "
                f"{self.config_directory.resolve()}"
            )

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        file_path = self.config_directory / filename

        if not file_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {file_path.resolve()}"
            )

        try:
            with file_path.open("r", encoding="utf-8") as file:
                content = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            raise ConfigurationError(
                f"Invalid YAML in {file_path}: {exc}"
            ) from exc

        if content is None:
            raise ConfigurationError(
                f"Configuration file is empty: {file_path.resolve()}"
            )

        if not isinstance(content, dict):
            raise ConfigurationError(
                f"Expected YAML object in {file_path.resolve()}"
            )

        return content

    def load_application_config(self) -> dict[str, Any]:
        return self._load_yaml("application.yaml")



    def load_collector_types(self) -> dict[str, Any]:
        config = self._load_yaml("collector_types.yaml")

        collector_types = config.get("collector_types")

        if not isinstance(collector_types, dict):
            raise ConfigurationError(
                "'collector_types' must be defined as an object "
                "in collector_types.yaml"
            )

        return collector_types

    def load_components(self) -> dict[str, Any]:
        config = self._load_yaml("components.yaml")

        components = config.get("components")

        if not isinstance(components, dict):
            raise ConfigurationError(
                "'components' must be defined as an object "
                "in components.yaml"
            )

        return components

    def load_entities(self) -> dict[str, Any]:
        config = self._load_yaml("entities.yaml")

        entities = config.get("entities")

        if not isinstance(entities, dict):
            raise ConfigurationError(
                "'entities' must be defined as an object "
                "in entities.yaml"
            )

        return entities

    def load_all(self) -> dict[str, Any]:
        return {
            "application": self.load_application_config(),
            "collector_types": self.load_collector_types(),
            "components": self.load_components(),
            "entities": self.load_entities(),
        }

    def load_reporting_config(self) -> dict[str, Any]:
        config = self._load_yaml("reporting.yaml")

        reporting = config.get("reporting")

        if not isinstance(reporting, dict):
            raise ConfigurationError(
                "'reporting' must be defined as an object "
                "in reporting.yaml"
            )

        return reporting