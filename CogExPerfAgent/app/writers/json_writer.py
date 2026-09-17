import json
import re
from pathlib import Path
from typing import Any


class JsonWriterError(Exception):
    """Raised when JSON output cannot be written."""


class JsonWriter:
    """Writes raw and normalized JSON result files."""

    def __init__(
        self,
        output_directory: str = "output",
    ) -> None:
        self.output_directory = Path(output_directory)

    @staticmethod
    def _safe_name(value: str) -> str:
        """Convert a value into a safe folder or file name."""

        cleaned_value = re.sub(
            r"[^A-Za-z0-9._-]+",
            "-",
            value.strip(),
        )

        return cleaned_value.strip("-") or "unknown"

    @staticmethod
    def _write_json(
        output_file: Path,
        result: dict[str, Any],
    ) -> Path:
        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            with output_file.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    result,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

        except (OSError, TypeError) as exc:
            raise JsonWriterError(
                f"Could not write JSON file "
                f"'{output_file}': {exc}"
            ) from exc

        return output_file

    def write_raw_result(
        self,
        execution_id: str,
        entity_name: str,
        component_name: str,
        collector_type: str,
        result: dict[str, Any],
    ) -> Path:
        """
        Write the raw Elasticsearch result.

        Output:
            output/<execution-id>/raw/<entity>/<component>/<collector>.json
        """

        output_file = (
            self.output_directory
            / self._safe_name(execution_id)
            / "raw"
            / self._safe_name(entity_name)
            / self._safe_name(component_name)
            / f"{self._safe_name(collector_type)}.json"
        )

        return self._write_json(
            output_file=output_file,
            result=result,
        )

    def write_timeseries_result(
        self,
        execution_id: str,
        entity_name: str,
        component_name: str,
        result: dict[str, Any],
    ) -> Path:
        """
        Write normalized long-format time-series data.

        Output:
            output/<execution-id>/aggregated/
            <entity>/<component>/timeseries.json
        """

        output_file = (
            self.output_directory
            / self._safe_name(execution_id)
            / "aggregated"
            / self._safe_name(entity_name)
            / self._safe_name(component_name)
            / "timeseries.json"
        )

        return self._write_json(
            output_file=output_file,
            result=result,
        )