import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

# Required when running on servers or Ubuntu without a display.
matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from app.result_aggregator.statistics import (
    StatisticsCalculator,
    StatisticsError,
)


class ChartBuilderError(Exception):
    """Raised when a performance chart cannot be generated."""


class KubernetesChartBuilder:
    """
    Generates Kubernetes performance reports from normalized
    time-series records.

    Entity report:
        One PNG containing one subplot per component and metric.
        Replica values are aggregated at each timestamp.

    Component report:
        One PNG per component containing one subplot per metric.
        Each pod/replica is displayed as a separate line.
    """

    def __init__(
        self,
        chart_config: dict[str, Any],
    ) -> None:
        if not isinstance(chart_config, dict):
            raise ChartBuilderError(
                "Chart configuration must be a dictionary."
            )

        self.chart_config = chart_config
        self.metric_configs = (
            self._get_enabled_metric_configs()
        )

    def build_entity_report(
        self,
        normalized_results: list[dict[str, Any]],
        output_directory: Path,
    ) -> Path | None:
        """
        Generate one entity-level PNG containing all component
        and metric graphs.

        For each component and timestamp, replica values are
        combined using the metric's component_aggregation method.
        """

        entity_config = self._get_report_config(
            "entity_report"
        )

        if entity_config.get("enabled", True) is False:
            return None

        if not normalized_results:
            raise ChartBuilderError(
                "No normalized component results were provided "
                "for the entity report."
            )

        plot_definitions: list[
            tuple[
                str,
                str,
                dict[str, Any],
                list[tuple[datetime, float]],
            ]
        ] = []

        entity_name = "unknown-entity"
        execution_id = "unknown-execution"

        for normalized_result in normalized_results:
            metadata, records = self._validate_result(
                normalized_result
            )

            entity_name = str(
                metadata.get(
                    "entity_name",
                    entity_name,
                )
            )

            execution_id = str(
                metadata.get(
                    "execution_id",
                    execution_id,
                )
            )

            component_name = str(
                metadata.get(
                    "component_name",
                    "unknown-component",
                )
            )

            component_display_name = str(
                metadata.get(
                    "component_display_name",
                    component_name,
                )
            )

            for (
                metric_name,
                metric_config,
            ) in self.metric_configs.items():

                aggregation_method = str(
                    metric_config.get(
                        "component_aggregation",
                        "avg",
                    )
                )

                points = self._build_component_average_series(
                    records=records,
                    metric_name=metric_name,
                    aggregation_method=aggregation_method,
                )

                plot_definitions.append(
                    (
                        component_display_name,
                        metric_name,
                        metric_config,
                        points,
                    )
                )

        if not plot_definitions:
            raise ChartBuilderError(
                "No entity chart data was found."
            )

        column_count = self._get_positive_integer(
            entity_config,
            "columns",
            len(self.metric_configs),
        )

        row_count = math.ceil(
            len(plot_definitions) / column_count
        )

        component_width = self._get_positive_number(
            entity_config,
            "component_width",
            8,
        )

        component_height = self._get_positive_number(
            entity_config,
            "component_height",
            4,
        )

        figure_width = column_count * component_width
        figure_height = row_count * component_height

        figure, axes = plt.subplots(
            nrows=row_count,
            ncols=column_count,
            figsize=(figure_width, figure_height),
            squeeze=False,
        )

        flat_axes = axes.flatten()

        for axis_index, plot_definition in enumerate(
            plot_definitions
        ):
            axis = flat_axes[axis_index]

            (
                component_display_name,
                metric_name,
                metric_config,
                points,
            ) = plot_definition

            display_name = str(
                metric_config.get(
                    "display_name",
                    metric_name,
                )
            )

            y_axis_label = str(
                metric_config.get(
                    "y_axis_label",
                    display_name,
                )
            )

            axis.set_title(
                f"{component_display_name} - {display_name}"
            )

            axis.set_ylabel(y_axis_label)
            axis.set_xlabel("Time (UTC)")

            self._configure_time_axis(axis)

            if points:
                timestamps = [
                    point[0]
                    for point in points
                ]

                values = [
                    point[1]
                    for point in points
                ]

                axis.plot(
                    timestamps,
                    values,
                    linewidth=1.8,
                    marker="o",
                    markersize=2.5,
                    label="Replica average",
                )

                axis.legend(
                    loc="best",
                    fontsize=8,
                )

            else:
                self._show_no_data(
                    axis,
                    "No data available",
                )

        # Hide unused subplot positions.
        for axis_index in range(
            len(plot_definitions),
            len(flat_axes),
        ):
            flat_axes[axis_index].set_visible(False)

        figure.suptitle(
            (
                f"{entity_name} Performance Report\n"
                f"Execution: {execution_id}"
            ),
            fontsize=16,
        )

        figure.tight_layout(
            rect=(0, 0, 1, 0.96)
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_name = str(
            entity_config.get(
                "file_name",
                "entity-performance-report.png",
            )
        )

        output_file = self._build_output_path(
            output_directory=output_directory,
            file_name=file_name,
        )

        self._save_figure(
            figure=figure,
            output_file=output_file,
        )

        return output_file

    def build_component_report(
        self,
        normalized_result: dict[str, Any],
        output_directory: Path,
    ) -> Path | None:
        """
        Generate one component-level PNG.

        Each enabled metric is displayed in a separate subplot.
        Each Kubernetes pod/replica appears as a separate line.
        """

        component_config = self._get_report_config(
            "component_report"
        )

        if component_config.get("enabled", True) is False:
            return None

        metadata, records = self._validate_result(
            normalized_result
        )

        component_name = str(
            metadata.get(
                "component_name",
                "unknown-component",
            )
        )

        component_display_name = str(
            metadata.get(
                "component_display_name",
                component_name,
            )
        )

        execution_id = str(
            metadata.get(
                "execution_id",
                "unknown-execution",
            )
        )

        series_field = str(
            component_config.get(
                "series_field",
                "kubernetes.pod.name",
            )
        )

        metric_count = len(self.metric_configs)

        if metric_count == 0:
            raise ChartBuilderError(
                "No chart metrics are enabled."
            )

        figure_width = self._get_positive_number(
            component_config,
            "width",
            14,
        )

        metric_height = self._get_positive_number(
            component_config,
            "metric_height",
            5,
        )

        figure_height = metric_count * metric_height

        figure, axes = plt.subplots(
            nrows=metric_count,
            ncols=1,
            figsize=(figure_width, figure_height),
            squeeze=False,
        )

        flat_axes = axes.flatten()

        for axis_index, (
            metric_name,
            metric_config,
        ) in enumerate(self.metric_configs.items()):

            axis = flat_axes[axis_index]

            display_name = str(
                metric_config.get(
                    "display_name",
                    metric_name,
                )
            )

            y_axis_label = str(
                metric_config.get(
                    "y_axis_label",
                    display_name,
                )
            )

            replica_series = self._build_replica_series(
                records=records,
                metric_name=metric_name,
                series_field=series_field,
            )

            axis.set_title(
                f"{component_display_name} - "
                f"{display_name} by Replica"
            )

            axis.set_ylabel(y_axis_label)
            axis.set_xlabel("Time (UTC)")

            self._configure_time_axis(axis)

            if replica_series:
                for (
                    replica_name,
                    points,
                ) in replica_series.items():

                    timestamps = [
                        point[0]
                        for point in points
                    ]

                    values = [
                        point[1]
                        for point in points
                    ]

                    axis.plot(
                        timestamps,
                        values,
                        linewidth=1.5,
                        marker="o",
                        markersize=2,
                        label=replica_name,
                    )

                axis.legend(
                    loc="upper left",
                    bbox_to_anchor=(1.01, 1),
                    fontsize=8,
                )

            else:
                self._show_no_data(
                    axis,
                    "No replica data available",
                )

        figure.suptitle(
            (
                f"{component_display_name} "
                f"Component Performance Report\n"
                f"Execution: {execution_id}"
            ),
            fontsize=15,
        )

        # Reserve space on the right for pod-name legends.
        figure.tight_layout(
            rect=(0, 0, 0.78, 0.95)
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_name = str(
            component_config.get(
                "file_name",
                "component-performance-report.png",
            )
        )

        output_file = self._build_output_path(
            output_directory=output_directory,
            file_name=file_name,
        )

        self._save_figure(
            figure=figure,
            output_file=output_file,
        )

        return output_file

    def _build_component_average_series(
        self,
        records: list[dict[str, Any]],
        metric_name: str,
        aggregation_method: str,
    ) -> list[tuple[datetime, float]]:
        """
        Aggregate all replica values for a component at each
        timestamp.
        """

        values_by_timestamp: dict[
            str,
            list[float],
        ] = defaultdict(list)

        for record in records:
            if not self._record_matches_metric(
                record=record,
                metric_name=metric_name,
            ):
                continue

            timestamp = record.get("timestamp")
            value = record.get("value")

            if not isinstance(timestamp, str):
                continue

            if not self._is_number(value):
                continue

            values_by_timestamp[timestamp].append(
                float(value)
            )

        points: list[tuple[datetime, float]] = []

        try:
            for timestamp, values in (
                values_by_timestamp.items()
            ):
                combined_value = (
                    StatisticsCalculator.combine(
                        values=values,
                        method=aggregation_method,
                    )
                )

                if combined_value is None:
                    continue

                points.append(
                    (
                        self._parse_timestamp(timestamp),
                        float(combined_value),
                    )
                )

        except StatisticsError as exc:
            raise ChartBuilderError(
                f"Could not aggregate metric "
                f"'{metric_name}' using "
                f"'{aggregation_method}': {exc}"
            ) from exc

        return sorted(
            points,
            key=lambda point: point[0],
        )

    def _build_replica_series(
        self,
        records: list[dict[str, Any]],
        metric_name: str,
        series_field: str,
    ) -> dict[str, list[tuple[datetime, float]]]:
        """
        Build a separate time-series line for each replica.

        Duplicate values for the same replica and timestamp are
        averaged before plotting.
        """

        replica_values: dict[
            str,
            dict[str, list[float]],
        ] = defaultdict(
            lambda: defaultdict(list)
        )

        for record in records:
            if not self._record_matches_metric(
                record=record,
                metric_name=metric_name,
            ):
                continue

            replica_name = record.get(series_field)
            timestamp = record.get("timestamp")
            value = record.get("value")

            if not replica_name:
                continue

            if not isinstance(timestamp, str):
                continue

            if not self._is_number(value):
                continue

            replica_values[str(replica_name)][
                timestamp
            ].append(float(value))

        replica_series: dict[
            str,
            list[tuple[datetime, float]],
        ] = {}

        for replica_name in sorted(replica_values):
            points: list[tuple[datetime, float]] = []

            for timestamp, values in (
                replica_values[replica_name].items()
            ):
                average_value = sum(values) / len(values)

                points.append(
                    (
                        self._parse_timestamp(timestamp),
                        average_value,
                    )
                )

            replica_series[replica_name] = sorted(
                points,
                key=lambda point: point[0],
            )

        return replica_series

    def _get_enabled_metric_configs(
        self,
    ) -> dict[str, dict[str, Any]]:
        metrics = self.chart_config.get(
            "metrics",
            {},
        )

        if not isinstance(metrics, dict):
            raise ChartBuilderError(
                "'reporting.charts.metrics' must be "
                "a dictionary."
            )

        enabled_metrics: dict[
            str,
            dict[str, Any],
        ] = {}

        for metric_name, metric_config in metrics.items():
            if not isinstance(metric_config, dict):
                continue

            if metric_config.get("enabled", False) is not True:
                continue

            enabled_metrics[str(metric_name)] = (
                metric_config
            )

        if not enabled_metrics:
            raise ChartBuilderError(
                "No chart metrics are enabled in "
                "reporting.yaml."
            )

        return enabled_metrics

    def _get_report_config(
        self,
        config_name: str,
    ) -> dict[str, Any]:
        config = self.chart_config.get(
            config_name,
            {},
        )

        if config is None:
            return {}

        if not isinstance(config, dict):
            raise ChartBuilderError(
                f"'reporting.charts.{config_name}' "
                f"must be a dictionary."
            )

        return config

    def _validate_result(
        self,
        normalized_result: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        if not isinstance(normalized_result, dict):
            raise ChartBuilderError(
                "Normalized result must be a dictionary."
            )

        metadata = normalized_result.get("metadata")
        records = normalized_result.get("records")

        if not isinstance(metadata, dict):
            raise ChartBuilderError(
                "Normalized metadata is missing or invalid."
            )

        if not isinstance(records, list):
            raise ChartBuilderError(
                "Normalized records are missing or invalid."
            )

        return metadata, records

    @staticmethod
    def _record_matches_metric(
        record: Any,
        metric_name: str,
    ) -> bool:
        if not isinstance(record, dict):
            return False

        if record.get("metric_name") != metric_name:
            return False

        # Some older normalized files may not have has_data.
        if record.get("has_data", True) is not True:
            return False

        return True

    @staticmethod
    def _configure_time_axis(
        axis: Any,
    ) -> None:
        locator = mdates.AutoDateLocator()

        axis.xaxis.set_major_locator(locator)
        axis.xaxis.set_major_formatter(
            mdates.ConciseDateFormatter(locator)
        )

        axis.grid(
            visible=True,
            alpha=0.3,
        )

        axis.tick_params(
            axis="x",
            labelrotation=25,
        )

    @staticmethod
    def _show_no_data(
        axis: Any,
        message: str,
    ) -> None:
        axis.text(
            0.5,
            0.5,
            message,
            horizontalalignment="center",
            verticalalignment="center",
            transform=axis.transAxes,
        )

    def _build_output_path(
        self,
        output_directory: Path,
        file_name: str,
    ) -> Path:
        chart_format = str(
            self.chart_config.get(
                "format",
                "png",
            )
        ).lower()

        safe_file_name = self._safe_name(file_name)

        output_file = (
            output_directory / safe_file_name
        )

        expected_suffix = f".{chart_format}"

        if output_file.suffix.lower() != expected_suffix:
            output_file = output_file.with_suffix(
                expected_suffix
            )

        return output_file

    def _save_figure(
        self,
        figure: Any,
        output_file: Path,
    ) -> None:
        dpi = self._get_positive_integer(
            self.chart_config,
            "dpi",
            150,
        )

        chart_format = str(
            self.chart_config.get(
                "format",
                "png",
            )
        ).lower()

        try:
            figure.savefig(
                output_file,
                dpi=dpi,
                format=chart_format,
                bbox_inches="tight",
            )

        except OSError as exc:
            raise ChartBuilderError(
                f"Could not write chart "
                f"'{output_file}': {exc}"
            ) from exc

        finally:
            plt.close(figure)

    @staticmethod
    def _parse_timestamp(
        timestamp: str,
    ) -> datetime:
        try:
            parsed_timestamp = datetime.fromisoformat(
                timestamp.replace(
                    "Z",
                    "+00:00",
                )
            )

        except ValueError as exc:
            raise ChartBuilderError(
                f"Invalid timestamp: {timestamp}"
            ) from exc

        if parsed_timestamp.tzinfo is None:
            parsed_timestamp = (
                parsed_timestamp.replace(
                    tzinfo=timezone.utc
                )
            )

        return parsed_timestamp.astimezone(
            timezone.utc
        )

    @staticmethod
    def _is_number(
        value: Any,
    ) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )

    @staticmethod
    def _get_positive_number(
        config: dict[str, Any],
        key: str,
        default_value: float,
    ) -> float:
        value = config.get(
            key,
            default_value,
        )

        try:
            numeric_value = float(value)

        except (TypeError, ValueError) as exc:
            raise ChartBuilderError(
                f"Invalid chart configuration "
                f"'{key}': {value}"
            ) from exc

        if numeric_value <= 0:
            raise ChartBuilderError(
                f"Chart configuration '{key}' "
                f"must be greater than zero."
            )

        return numeric_value

    @staticmethod
    def _get_positive_integer(
        config: dict[str, Any],
        key: str,
        default_value: int,
    ) -> int:
        value = config.get(
            key,
            default_value,
        )

        try:
            integer_value = int(value)

        except (TypeError, ValueError) as exc:
            raise ChartBuilderError(
                f"Invalid chart configuration "
                f"'{key}': {value}"
            ) from exc

        if integer_value <= 0:
            raise ChartBuilderError(
                f"Chart configuration '{key}' "
                f"must be greater than zero."
            )

        return integer_value

    @staticmethod
    def _safe_name(
        value: str,
    ) -> str:
        safe_value = re.sub(
            r"[^A-Za-z0-9._-]+",
            "-",
            value.strip(),
        )

        return safe_value.strip("-") or "chart.png"