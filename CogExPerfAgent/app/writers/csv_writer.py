import csv
import re
from pathlib import Path
from typing import Any


class CsvWriterError(Exception):
    """Raised when CSV output cannot be written."""


class CsvWriter:
    """Writes normalized long-format and wide-format CSV files."""

    def __init__(
        self,
        output_directory: str = "output",
    ) -> None:
        self.output_directory = Path(output_directory)

    @staticmethod
    def _safe_name(value: str) -> str:
        cleaned_value = re.sub(
            r"[^A-Za-z0-9._-]+",
            "-",
            value.strip(),
        )

        return cleaned_value.strip("-") or "unknown"
    def _get_entity_directory(
        self,
        execution_id: str,
        entity_name: str,
    ) -> Path:
        entity_directory = (
            self.output_directory
            / self._safe_name(execution_id)
            / "aggregated"
            / self._safe_name(entity_name)
        )

        entity_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return entity_directory

    @staticmethod
    def _write_summary_csv(
        output_file: Path,
        columns: list[str],
        rows: list[dict[str, Any]],
    ) -> Path:
        """
        Write summary rows using the configured column list.

        Raises an error when reporting.yaml contains a column
        that is not produced by the summary builder.
        """

        if not isinstance(columns, list) or not columns:
            raise CsvWriterError(
                "Summary CSV columns must be a non-empty list."
            )

        invalid_columns = [
            column
            for column in columns
            if rows
            and not any(
                column in row
                for row in rows
            )
        ]

        if invalid_columns:
            raise CsvWriterError(
                "The following configured summary columns are "
                "not produced by the summary builder: "
                + ", ".join(invalid_columns)
            )

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            with output_file.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=columns,
                    extrasaction="ignore",
                )

                writer.writeheader()
                writer.writerows(rows)

        except (OSError, csv.Error) as exc:
            raise CsvWriterError(
                f"Could not write summary CSV "
                f"'{output_file}': {exc}"
            ) from exc

        return output_file

    def write_pod_summary(
        self,
        execution_id: str,
        entity_name: str,
        component_name: str,
        rows: list[dict[str, Any]],
        columns: list[str],
        file_name: str = "pod-summary.csv",
    ) -> Path:
        """
        Write pod-level summary using columns selected
        in reporting.yaml.
        """

        if not isinstance(columns, list) or not columns:
            raise CsvWriterError(
                "Pod summary columns must be a non-empty list."
            )

        output_file = (
            self._get_component_directory(
                execution_id=execution_id,
                entity_name=entity_name,
                component_name=component_name,
            )
            / self._safe_name(file_name)
        )

        return self._write_summary_csv(
            output_file=output_file,
            columns=columns,
            rows=rows,
        )
    def write_entity_summary(
        self,
        execution_id: str,
        entity_name: str,
        rows: list[dict[str, Any]],
        columns: list[str],
        file_name: str = "entity-summary.csv",
    ) -> Path:
        """
        Write entity-level summary using columns selected
        in reporting.yaml.
        """

        if not isinstance(columns, list) or not columns:
            raise CsvWriterError(
                "Entity summary columns must be a non-empty list."
            )

        output_file = (
            self._get_entity_directory(
                execution_id=execution_id,
                entity_name=entity_name,
            )
            / self._safe_name(file_name)
        )

        return self._write_summary_csv(
            output_file=output_file,
            columns=columns,
            rows=rows,
        )


    def _get_component_directory(
        self,
        execution_id: str,
        entity_name: str,
        component_name: str,
    ) -> Path:
        target_directory = (
            self.output_directory
            / self._safe_name(execution_id)
            / "aggregated"
            / self._safe_name(entity_name)
            / self._safe_name(component_name)
        )

        target_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return target_directory

    def write_long_timeseries(
        self,
        execution_id: str,
        entity_name: str,
        component_name: str,
        normalized_result: dict[str, Any],
    ) -> Path:
        """
        Write one row for every timestamp and metric.

        Example:

            timestamp, pod, metric_name, value
            07:00:30, pod-1, cpu_pct, 12.4
            07:00:30, pod-1, mem_pct, 32.1
        """

        columns = normalized_result.get("columns")
        records = normalized_result.get("records")

        if not isinstance(columns, list) or not columns:
            raise CsvWriterError(
                "Normalized result does not contain valid columns."
            )

        if not isinstance(records, list):
            raise CsvWriterError(
                "Normalized result does not contain valid records."
            )

        output_file = (
            self._get_component_directory(
                execution_id=execution_id,
                entity_name=entity_name,
                component_name=component_name,
            )
            / "timeseries.csv"
        )

        try:
            with output_file.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=columns,
                    extrasaction="ignore",
                )

                writer.writeheader()
                writer.writerows(records)

        except (OSError, csv.Error) as exc:
            raise CsvWriterError(
                f"Could not write CSV file "
                f"'{output_file}': {exc}"
            ) from exc

        return output_file

    def write_wide_timeseries(
        self,
        execution_id: str,
        entity_name: str,
        component_name: str,
        normalized_result: dict[str, Any],
    ) -> Path:
        """
        Convert long-format records into a human-readable wide table.

        Example:

            timestamp, pod, cpu_pct, cpu_nanocores, mem_pct, mem_bytes
        """

        metadata = normalized_result.get("metadata")
        records = normalized_result.get("records")

        if not isinstance(metadata, dict):
            raise CsvWriterError(
                "Normalized metadata is missing or invalid."
            )

        if not isinstance(records, list):
            raise CsvWriterError(
                "Normalized records are missing or invalid."
            )

        group_fields = metadata.get(
            "group_fields",
            [],
        )

        metric_names = metadata.get(
            "metric_names",
            [],
        )

        if not isinstance(group_fields, list):
            raise CsvWriterError(
                "Normalized group_fields must be a list."
            )

        if not isinstance(metric_names, list):
            raise CsvWriterError(
                "Normalized metric_names must be a list."
            )

        base_columns = [
            "execution_id",
            "entity_name",
            "component_name",
            "collector_type",
            "timestamp",
            *group_fields,
        ]

        output_columns = [
            *base_columns,
            *metric_names,
        ]

        pivoted_rows: dict[
            tuple[Any, ...],
            dict[str, Any],
        ] = {}

        for record in records:
            if not isinstance(record, dict):
                continue

            row_key = tuple(
                record.get(column)
                for column in base_columns
            )

            if row_key not in pivoted_rows:
                pivoted_rows[row_key] = {
                    column: record.get(column)
                    for column in base_columns
                }

            metric_name = record.get("metric_name")

            if (
                isinstance(metric_name, str)
                and metric_name in metric_names
            ):
                pivoted_rows[row_key][metric_name] = (
                    record.get("value")
                )

        output_file = (
            self._get_component_directory(
                execution_id=execution_id,
                entity_name=entity_name,
                component_name=component_name,
            )
            / "timeseries-wide.csv"
        )

        try:
            with output_file.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=output_columns,
                    extrasaction="ignore",
                )

                writer.writeheader()

                for row in pivoted_rows.values():
                    writer.writerow(row)

        except (OSError, csv.Error) as exc:
            raise CsvWriterError(
                f"Could not write wide CSV file "
                f"'{output_file}': {exc}"
            ) from exc

        return output_file