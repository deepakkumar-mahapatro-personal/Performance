import json
import csv
import html
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from app.rule_analyzer.analyzer import (
    RuleAnalyzer,
    RuleAnalyzerError,
)


class HtmlReportError(Exception):
    """Raised when an HTML performance report cannot be generated."""


class HtmlReportBuilder:
    """
    Builds one HTML report containing:

    - Entity-level performance graphs
    - Entity summary statistics
    - Component-level replica graphs
    - Pod-level summary statistics
    """

    def __init__(
        self,
        report_config: dict[str, Any],
        rules_config: dict[str, Any] | None = None,
        rules_config_error: str | None = None,
    ) -> None:
        if not isinstance(report_config, dict):
            raise HtmlReportError(
                "HTML report configuration must be a dictionary."
            )

        self.report_config = report_config
        self.rules_config = rules_config or {}
        self.rules_config_error = rules_config_error

    @staticmethod
    def _get_test_timeframe(
        aggregated_directory: Path,
    ) -> tuple[str, str]:
        """
        Find the earliest and latest timestamps from all component
        timeseries.json files.
        """

        timestamps: list[datetime] = []

        timeseries_files = sorted(
            aggregated_directory.glob(
                "*/timeseries.json"
            )
        )

        for timeseries_file in timeseries_files:
            try:
                with timeseries_file.open(
                    "r",
                    encoding="utf-8",
                ) as file:
                    data = json.load(file)

            except (
                OSError,
                json.JSONDecodeError,
            ):
                continue

            records = data.get(
                "records",
                [],
            )

            if not isinstance(records, list):
                continue

            for record in records:
                if not isinstance(record, dict):
                    continue

                timestamp = record.get(
                    "timestamp"
                )

                if not isinstance(timestamp, str):
                    continue

                try:
                    parsed_timestamp = (
                        datetime.fromisoformat(
                            timestamp.replace(
                                "Z",
                                "+00:00",
                            )
                        )
                    )

                except ValueError:
                    continue

                timestamps.append(
                    parsed_timestamp
                )

        if not timestamps:
            return "N/A", "N/A"

        start_time = min(timestamps)
        end_time = max(timestamps)

        return (
            start_time.strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            end_time.strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
        )
    def build_report(
        self,
        output_directory: str,
        execution_id: str,
        entity_name: str,
    ) -> Path:
        execution_directory = (
            Path(output_directory)
            / execution_id
        )

        aggregated_directory = (
            execution_directory
            / "aggregated"
            / entity_name
        )
        start_time, end_time = (
            self._get_test_timeframe(
                aggregated_directory
            )
        )
        visualization_directory = (
            execution_directory
            / "visualizations"
            / entity_name
        )

        report_directory = (
            execution_directory
            / "reports"
            / entity_name
        )

        report_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_name = f"{execution_id}_PSR_Report.html"

        report_file = report_directory / file_name

        entity_summary_file = (
            aggregated_directory
            / "entity-summary.csv"
        )

        if not entity_summary_file.is_file():
            raise HtmlReportError(
                f"Entity summary file was not found: "
                f"{entity_summary_file}"
            )

        entity_columns, entity_rows = self._read_csv(
            entity_summary_file
        )

        rule_evaluation = self._evaluate_rules(
            entity_rows
        )

        component_names = self._get_component_names(
            entity_rows
        )

        component_reports: list[dict[str, Any]] = []

        for component_name in component_names:
            pod_summary_file = (
                aggregated_directory
                / component_name
                / "pod-summary.csv"
            )

            component_chart_file = (
                visualization_directory
                / component_name
                / "component-performance-report.png"
            )

            pod_columns: list[str] = []
            pod_rows: list[dict[str, str]] = []

            if pod_summary_file.is_file():
                pod_columns, pod_rows = self._read_csv(
                    pod_summary_file
                )

            component_reports.append(
                {
                    "component_name": component_name,
                    "chart_file": component_chart_file,
                    "pod_summary_file": pod_summary_file,
                    "pod_columns": pod_columns,
                    "pod_rows": pod_rows,
                }
            )

        entity_chart_file = (
            visualization_directory
            / "entity-performance-report.png"
        )

        report_content = self._build_html(
            report_file=report_file,
            execution_id=execution_id,
            entity_name=entity_name,
            entity_chart_file=entity_chart_file,
            entity_summary_file=entity_summary_file,
            entity_columns=entity_columns,
            rule_evaluation=rule_evaluation,
            start_time=start_time,
            end_time=end_time,
            entity_rows=entity_rows,
            component_reports=component_reports,
        )

        try:
            report_file.write_text(
                report_content,
                encoding="utf-8",
            )

        except OSError as exc:
            raise HtmlReportError(
                f"Could not write HTML report "
                f"'{report_file}': {exc}"
            ) from exc

        return report_file

    def _evaluate_rules(
        self,
        entity_rows: list[dict[str, str]],
    ) -> dict[str, Any]:
        """
        Evaluate configured performance rules.

        Rule failures do not prevent HTML report generation.
        """

        if self.rules_config_error:
            return {
                "enabled": True,
                "overall_status": "ERROR",
                "total_rules": 0,
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "failed_components": [],
                "results": [],
                "error_message": self.rules_config_error,
            }

        try:
            analyzer = RuleAnalyzer(
                rules_config=self.rules_config
            )

            return analyzer.evaluate(
                summary_rows=entity_rows
            )

        except RuleAnalyzerError as exc:
            return {
                "enabled": True,
                "overall_status": "ERROR",
                "total_rules": 0,
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "failed_components": [],
                "results": [],
                "error_message": str(exc),
            }

    @staticmethod
    def _render_rule_evaluation(
        evaluation: dict[str, Any],
    ) -> str:
        status = str(
            evaluation.get(
                "overall_status",
                "NOT_EVALUATED",
            )
        )

        if status == "NOT_EVALUATED":
            return """
    <section class="section">
        <h2>Performance Validation</h2>

        <div class="result-banner result-neutral">
            TEST RESULT: NOT EVALUATED
        </div>
    </section>
    """

        if status == "ERROR":
            error_message = html.escape(
                str(
                    evaluation.get(
                        "error_message",
                        "Rule evaluation could not be completed.",
                    )
                )
            )

            return f"""
    <section class="section">
        <h2>Performance Validation</h2>

        <div class="result-banner result-error">
            TEST RESULT: ERROR
        </div>

        <div class="warning">
            {error_message}
        </div>
    </section>
    """

        if status == "PASS":
            status_class = "result-pass"
        else:
            status_class = "result-fail"

        passed_checks = evaluation.get(
            "passed_checks",
            0,
        )

        failed_checks = evaluation.get(
            "failed_checks",
            0,
        )

        total_checks = evaluation.get(
            "total_checks",
            0,
        )

        table_rows: list[str] = []

        for result in evaluation.get(
            "results",
            [],
        ):
            result_status = str(
                result.get(
                    "status",
                    "",
                )
            )

            row_status_class = (
                "check-pass"
                if result_status == "PASS"
                else "check-fail"
            )

            actual_value = result.get(
                "actual_value"
            )

            if actual_value is None:
                actual_display = "-"
            else:
                actual_display = (
                    f"{float(actual_value):.2f}"
                )

            threshold = result.get(
                "threshold"
            )

            threshold_display = (
                f"{float(threshold):.2f}"
                if threshold is not None
                else "-"
            )

            check_display = (
                f"{html.escape(str(result.get('statistic', '')))} "
                f"{html.escape(str(result.get('operator', '')))} "
                f"{html.escape(threshold_display)}"
            )

            table_rows.append(
                f"""
    <tr>
        <td>{html.escape(str(result.get("component_name", "")))}</td>
        <td>{html.escape(str(result.get("metric_name", "")))}</td>
        <td>{html.escape(str(result.get("description", "")))}</td>
        <td>{check_display}</td>
        <td>{html.escape(actual_display)}</td>
        <td>
            <span class="{row_status_class}">
                {html.escape(result_status)}
            </span>
        </td>
    </tr>
    """
            )

        return f"""
    <section class="section">
        <h2>Performance Validation</h2>

        <div class="result-banner {status_class}">
            TEST RESULT: {html.escape(status)}
        </div>

        <div class="rule-summary">
            <div>
                <strong>{total_checks}</strong>
                Checks
            </div>

            <div>
                <strong>{passed_checks}</strong>
                Passed
            </div>

            <div>
                <strong>{failed_checks}</strong>
                Failed
            </div>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Component</th>
                        <th>Metric</th>
                        <th>Rule</th>
                        <th>Expected</th>
                        <th>Actual</th>
                        <th>Result</th>
                    </tr>
                </thead>

                <tbody>
                    {''.join(table_rows)}
                </tbody>
            </table>
        </div>
    </section>
    """

    def _build_html(
        self,
        report_file: Path,
        execution_id: str,
        entity_name: str,
        entity_chart_file: Path,
        entity_summary_file: Path,
        entity_columns: list[str],
        entity_rows: list[dict[str, str]],
        component_reports: list[dict[str, Any]],
        rule_evaluation: dict[str, Any],
        start_time: str,
        end_time: str,
    ) -> str:
        report_title = f"{entity_name}_PSR_Report"

        include_entity_summary = bool(
            self.report_config.get(
                "include_entity_summary",
                True,
            )
        )

        include_component_summaries = bool(
            self.report_config.get(
                "include_component_summaries",
                True,
            )
        )

        generated_time = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC")

        metric_names = sorted(
            {
                row.get("metric_name", "")
                for row in entity_rows
                if row.get("metric_name")
            }
        )

        total_pod_rows = sum(
            len(component["pod_rows"])
            for component in component_reports
        )

        sections: list[str] = []

        sections.append(
            self._render_header(
                report_title=report_title,
                execution_id=execution_id,
                entity_name=entity_name,
                start_time=start_time,
                end_time=end_time,
                generated_time=generated_time,
            )
        )

        sections.append(
            self._render_rule_evaluation(
                evaluation=rule_evaluation
            )
        )

        sections.append(
            self._render_overview_cards(
                component_count=len(component_reports),
                metric_count=len(metric_names),
                entity_row_count=len(entity_rows),
                pod_row_count=total_pod_rows,
            )
        )

        sections.append(
            self._render_entity_chart(
                report_file=report_file,
                entity_chart_file=entity_chart_file,
            )
        )

        if include_entity_summary:
            sections.append(
                self._render_summary_section(
                    section_title="Entity Summary",
                    report_file=report_file,
                    csv_file=entity_summary_file,
                    columns=entity_columns,
                    rows=entity_rows,
                )
            )

        sections.append(
            '<section class="section">'
            '<h2>Component Reports</h2>'
            '<p class="section-description">'
            "Each component graph displays one line per "
            "Kubernetes replica."
            "</p>"
            "</section>"
        )

        for component in component_reports:
            sections.append(
                self._render_component_section(
                    report_file=report_file,
                    component=component,
                    include_summary=(
                        include_component_summaries
                    ),
                )
            )

        document_body = "\n".join(sections)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
    <title>{html.escape(report_title)}</title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            padding: 0;
            background: #f4f6f8;
            color: #1f2933;
            font-family:
                Arial,
                Helvetica,
                sans-serif;
        }}

        .page {{
            width: 96%;
            max-width: 1800px;
            margin: 24px auto;
        }}

        .result-banner {{
            padding: 18px;
            margin: 12px 0 18px 0;
            border-radius: 8px;
            font-size: 22px;
            font-weight: bold;
            text-align: center;
        }}

        .result-pass {{
            background: #e6f4ea;
            color: #176b34;
            border: 1px solid #9bd4ad;
        }}

        .result-fail {{
            background: #fdecec;
            color: #a61b1b;
            border: 1px solid #efaaaa;
        }}

        .result-error {{
            background: #fff4e5;
            color: #8a4b08;
            border: 1px solid #efc27d;
        }}

        .result-neutral {{
            background: #edf2f7;
            color: #52606d;
            border: 1px solid #cbd5e1;
        }}

        .rule-summary {{
            display: flex;
            gap: 14px;
            margin-bottom: 18px;
            flex-wrap: wrap;
        }}

        .rule-summary div {{
            background: #f7f9fb;
            border: 1px solid #d9e2ec;
            padding: 10px 18px;
            border-radius: 6px;
        }}

        .rule-summary strong {{
            margin-right: 5px;
        }}

        .check-pass {{
            font-weight: bold;
            color: #176b34;
        }}

        .check-fail {{
            font-weight: bold;
            color: #a61b1b;
        }}

        .header {{
            background: white;
            border-radius: 10px;
            padding: 24px 28px;
            margin-bottom: 20px;
            box-shadow:
                0 2px 8px rgba(0, 0, 0, 0.08);
        }}

        .header h1 {{
            margin: 0 0 16px 0;
            font-size: 28px;
        }}

        .metadata-grid {{
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(240px, 1fr));
            gap: 12px;
        }}

        .metadata-item {{
            background: #f7f9fb;
            border-radius: 6px;
            padding: 10px 12px;
        }}

        .metadata-label {{
            display: block;
            color: #52606d;
            font-size: 12px;
            margin-bottom: 4px;
            text-transform: uppercase;
        }}

        .metadata-value {{
            font-weight: bold;
            word-break: break-word;
        }}

        .overview {{
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin-bottom: 20px;
        }}

        .overview-card {{
            background: white;
            border-radius: 8px;
            padding: 18px;
            text-align: center;
            box-shadow:
                0 2px 8px rgba(0, 0, 0, 0.07);
        }}

        .overview-value {{
            display: block;
            font-size: 26px;
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .overview-label {{
            color: #52606d;
            font-size: 13px;
        }}

        .section {{
            background: white;
            border-radius: 10px;
            padding: 22px;
            margin-bottom: 20px;
            box-shadow:
                0 2px 8px rgba(0, 0, 0, 0.07);
        }}

        .section h2 {{
            margin-top: 0;
            margin-bottom: 8px;
        }}

        .section h3 {{
            margin-top: 0;
        }}

        .section-description {{
            color: #52606d;
            margin-top: 0;
        }}

        .chart-container {{
            text-align: center;
            overflow-x: auto;
        }}

        .chart-image {{
            width: 100%;
            height: auto;
            max-width: 1700px;
            border: 1px solid #d9e2ec;
            border-radius: 6px;
        }}

        .table-container {{
            overflow-x: auto;
            max-height: 650px;
            overflow-y: auto;
            border: 1px solid #d9e2ec;
            border-radius: 6px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            background: white;
        }}

        th {{
            position: sticky;
            top: 0;
            background: #e9eff5;
            color: #243b53;
            z-index: 1;
        }}

        th,
        td {{
            padding: 9px 10px;
            border-bottom: 1px solid #d9e2ec;
            text-align: left;
            white-space: nowrap;
        }}

        tbody tr:nth-child(even) {{
            background: #f8fafc;
        }}

        tbody tr:hover {{
            background: #edf2f7;
        }}

        .download-link {{
            display: inline-block;
            margin: 8px 0 14px 0;
            padding: 8px 12px;
            border-radius: 5px;
            background: #e9eff5;
            color: #243b53;
            text-decoration: none;
            font-size: 13px;
            font-weight: bold;
        }}

        .download-link:hover {{
            background: #d9e2ec;
        }}

        .warning {{
            background: #fff7e6;
            border: 1px solid #f5c26b;
            border-radius: 5px;
            padding: 12px;
            color: #7c4a03;
        }}

        .component-heading {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }}

        .footer {{
            text-align: center;
            color: #7b8794;
            font-size: 12px;
            padding: 14px;
        }}

        @media print {{
            body {{
                background: white;
            }}

            .page {{
                width: 100%;
                margin: 0;
            }}

            .section,
            .header,
            .overview-card {{
                box-shadow: none;
                break-inside: avoid;
            }}

            .download-link {{
                display: none;
            }}
        }}
    </style>
</head>

<body>
    <main class="page">
        {document_body}

        <footer class="footer">
            Generated by CogExPerfAgent
        </footer>
    </main>
</body>
</html>
"""

    @staticmethod
    def _render_header(
        report_title: str,
        execution_id: str,
        entity_name: str,
        start_time: str,
        end_time: str,
        generated_time: str,
    ) -> str:
        return f"""
<section class="header">
    <h1>{html.escape(report_title)}</h1>

    <div class="metadata-grid">
        <div class="metadata-item">
            <span class="metadata-label">Execution ID</span>
            <span class="metadata-value">
                {html.escape(execution_id)}
            </span>
        </div>

        <div class="metadata-item">
            <span class="metadata-label">Entity</span>
            <span class="metadata-value">
                {html.escape(entity_name)}
            </span>
        </div>
        <div class="metadata-item">
            <span class="metadata-label">
                Start Time
            </span>
            <span class="metadata-value">
                {html.escape(start_time)}
            </span>
        </div>

        <div class="metadata-item">
            <span class="metadata-label">
                End Time
            </span>
            <span class="metadata-value">
                {html.escape(end_time)}
            </span>
        </div>
        <div class="metadata-item">
            <span class="metadata-label">Generated</span>
            <span class="metadata-value">
                {html.escape(generated_time)}
            </span>
        </div>
    </div>
</section>
"""

    @staticmethod
    def _render_overview_cards(
        component_count: int,
        metric_count: int,
        entity_row_count: int,
        pod_row_count: int,
    ) -> str:
        return f"""
<section class="overview">
    <div class="overview-card">
        <span class="overview-value">
            {component_count}
        </span>
        <span class="overview-label">
            Components
        </span>
    </div>

    <div class="overview-card">
        <span class="overview-value">
            {metric_count}
        </span>
        <span class="overview-label">
            Metrics
        </span>
    </div>

    <div class="overview-card">
        <span class="overview-value">
            {entity_row_count}
        </span>
        <span class="overview-label">
            Entity Summary Rows
        </span>
    </div>

    <div class="overview-card">
        <span class="overview-value">
            {pod_row_count}
        </span>
        <span class="overview-label">
            Pod Summary Rows
        </span>
    </div>
</section>
"""

    def _render_entity_chart(
        self,
        report_file: Path,
        entity_chart_file: Path,
    ) -> str:
        if not entity_chart_file.is_file():
            return """
<section class="section">
    <h2>Entity Performance Graphs</h2>
    <div class="warning">
        Entity performance graph was not found.
    </div>
</section>
"""

        relative_path = self._relative_path(
            source_file=entity_chart_file,
            report_file=report_file,
        )

        return f"""
<section class="section">
    <h2>Entity Performance Graphs</h2>

    <p class="section-description">
        Each graph shows the configured aggregation of all
        active replicas for that component and timestamp.
    </p>

    <div class="chart-container">
        <img
            class="chart-image"
            src="{html.escape(relative_path)}"
            alt="Entity performance graphs"
        >
    </div>
</section>
"""

    def _render_summary_section(
        self,
        section_title: str,
        report_file: Path,
        csv_file: Path,
        columns: list[str],
        rows: list[dict[str, str]],
    ) -> str:
        download_path = self._relative_path(
            source_file=csv_file,
            report_file=report_file,
        )

        table_html = self._render_table(
            columns=columns,
            rows=rows,
        )

        return f"""
<section class="section">
    <h2>{html.escape(section_title)}</h2>

    <a
        class="download-link"
        href="{html.escape(download_path)}"
    >
        Open CSV
    </a>

    {table_html}
</section>
"""

    def _render_component_section(
        self,
        report_file: Path,
        component: dict[str, Any],
        include_summary: bool,
    ) -> str:
        component_name = str(
            component["component_name"]
        )

        component_chart_file = Path(
            component["chart_file"]
        )

        pod_summary_file = Path(
            component["pod_summary_file"]
        )

        pod_columns = component["pod_columns"]
        pod_rows = component["pod_rows"]

        content_parts: list[str] = []

        content_parts.append(
            f"""
<section class="section">
    <div class="component-heading">
        <h2>{html.escape(component_name)}</h2>
    </div>
"""
        )

        if component_chart_file.is_file():
            chart_path = self._relative_path(
                source_file=component_chart_file,
                report_file=report_file,
            )

            content_parts.append(
                f"""
    <div class="chart-container">
        <img
            class="chart-image"
            src="{html.escape(chart_path)}"
            alt="{html.escape(component_name)} performance graph"
        >
    </div>
"""
            )
        else:
            content_parts.append(
                """
    <div class="warning">
        Component performance graph was not found.
    </div>
"""
            )

        if include_summary:
            content_parts.append(
                "<h3>Pod Summary</h3>"
            )

            if pod_summary_file.is_file():
                csv_path = self._relative_path(
                    source_file=pod_summary_file,
                    report_file=report_file,
                )

                content_parts.append(
                    f"""
    <a
        class="download-link"
        href="{html.escape(csv_path)}"
    >
        Open Pod Summary CSV
    </a>
"""
                )

                content_parts.append(
                    self._render_table(
                        columns=pod_columns,
                        rows=pod_rows,
                    )
                )
            else:
                content_parts.append(
                    """
    <div class="warning">
        Pod summary CSV was not found.
    </div>
"""
                )

        content_parts.append("</section>")

        return "\n".join(content_parts)

    @staticmethod
    def _render_table(
        columns: list[str],
        rows: list[dict[str, str]],
    ) -> str:
        if not columns:
            return (
                '<div class="warning">'
                "No table columns were found."
                "</div>"
            )

        header_cells = "".join(
            f"<th>{html.escape(column)}</th>"
            for column in columns
        )

        body_rows: list[str] = []

        for row in rows:
            cells = "".join(
                (
                    "<td>"
                    f"{html.escape(str(row.get(column, '')))}"
                    "</td>"
                )
                for column in columns
            )

            body_rows.append(
                f"<tr>{cells}</tr>"
            )

        if not body_rows:
            body_rows.append(
                (
                    '<tr><td colspan="'
                    f'{len(columns)}">'
                    "No data available"
                    "</td></tr>"
                )
            )

        return f"""
<div class="table-container">
    <table>
        <thead>
            <tr>{header_cells}</tr>
        </thead>
        <tbody>
            {''.join(body_rows)}
        </tbody>
    </table>
</div>
"""

    @staticmethod
    def _read_csv(
        file_path: Path,
    ) -> tuple[list[str], list[dict[str, str]]]:
        try:
            with file_path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as file:
                reader = csv.DictReader(file)

                columns = list(
                    reader.fieldnames or []
                )

                rows = [
                    {
                        key: value or ""
                        for key, value in row.items()
                    }
                    for row in reader
                ]

        except OSError as exc:
            raise HtmlReportError(
                f"Could not read CSV file "
                f"'{file_path}': {exc}"
            ) from exc

        return columns, rows

    @staticmethod
    def _get_component_names(
        entity_rows: list[dict[str, str]],
    ) -> list[str]:
        return sorted(
            {
                row["component_name"]
                for row in entity_rows
                if row.get("component_name")
            }
        )

    @staticmethod
    def _relative_path(
        source_file: Path,
        report_file: Path,
    ) -> str:
        relative_path = os.path.relpath(
            source_file,
            start=report_file.parent,
        )

        return Path(relative_path).as_posix()