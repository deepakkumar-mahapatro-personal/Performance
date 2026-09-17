from typing import Any, Callable


class RuleAnalyzerError(Exception):
    """Raised when rule evaluation cannot be completed."""


class RuleAnalyzer:
    """
    Evaluate performance rules against entity-summary rows.

    The analyzer does not read or write files.
    It accepts summary rows and returns evaluation results.

    This allows the same analyzer to be reused by:

        - HTML reporting
        - Future AI analysis
        - Future API integrations
    """

    OPERATORS: dict[
        str,
        Callable[[float, float], bool],
    ] = {
        "<=": lambda actual, threshold: actual <= threshold,
        ">=": lambda actual, threshold: actual >= threshold,
        "<": lambda actual, threshold: actual < threshold,
        ">": lambda actual, threshold: actual > threshold,
        "==": lambda actual, threshold: actual == threshold,
        "!=": lambda actual, threshold: actual != threshold,
    }

    def __init__(
        self,
        rules_config: dict[str, Any],
    ) -> None:
        if not isinstance(rules_config, dict):
            raise RuleAnalyzerError(
                "Rules configuration must be a dictionary."
            )

        analyzer_config = rules_config.get(
            "rule_analyzer",
            {},
        )

        if not isinstance(analyzer_config, dict):
            raise RuleAnalyzerError(
                "'rule_analyzer' must be a dictionary."
            )

        self.config = analyzer_config

    def evaluate(
        self,
        summary_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Evaluate all enabled rules.

        Returns an overall PASS/FAIL result together with
        individual rule-check results.
        """

        if self.config.get("enabled", False) is not True:
            return {
                "enabled": False,
                "overall_status": "NOT_EVALUATED",
                "total_rules": 0,
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "failed_components": [],
                "results": [],
            }

        if not isinstance(summary_rows, list):
            raise RuleAnalyzerError(
                "Summary rows must be a list."
            )

        rules = self.config.get(
            "rules",
            [],
        )

        if not isinstance(rules, list):
            raise RuleAnalyzerError(
                "'rule_analyzer.rules' must be a list."
            )

        enabled_rules = [
            rule
            for rule in rules
            if isinstance(rule, dict)
            and rule.get("enabled", True) is True
        ]

        results: list[dict[str, Any]] = []

        for rule in enabled_rules:
            results.extend(
                self._evaluate_rule(
                    rule=rule,
                    summary_rows=summary_rows,
                )
            )

        passed_checks = sum(
            1
            for result in results
            if result["status"] == "PASS"
        )

        failed_checks = sum(
            1
            for result in results
            if result["status"] == "FAIL"
        )

        failed_components = sorted(
            {
                str(result["component_name"])
                for result in results
                if result["status"] == "FAIL"
                and result.get("component_name")
            }
        )

        overall_status = (
            "FAIL"
            if failed_checks > 0
            else "PASS"
        )

        return {
            "enabled": True,
            "overall_status": overall_status,
            "total_rules": len(enabled_rules),
            "total_checks": len(results),
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "failed_components": failed_components,
            "results": results,
        }

    def _evaluate_rule(
        self,
        rule: dict[str, Any],
        summary_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rule_id = str(
            rule.get(
                "rule_id",
                "",
            )
        ).strip()

        if not rule_id:
            raise RuleAnalyzerError(
                "Every enabled rule must have a rule_id."
            )

        description = str(
            rule.get(
                "description",
                rule_id,
            )
        )

        component_name = str(
            rule.get(
                "component_name",
                "*",
            )
        )

        metric_name = rule.get(
            "metric_name"
        )

        statistic = str(
            rule.get(
                "statistic",
                "",
            )
        ).strip()

        if not statistic:
            raise RuleAnalyzerError(
                f"Rule '{rule_id}' does not define "
                f"a statistic."
            )

        operator = str(
            rule.get(
                "operator",
                "",
            )
        ).strip()

        comparison = self.OPERATORS.get(
            operator
        )

        if comparison is None:
            raise RuleAnalyzerError(
                f"Rule '{rule_id}' uses unsupported "
                f"operator '{operator}'."
            )

        if "threshold" not in rule:
            raise RuleAnalyzerError(
                f"Rule '{rule_id}' does not define "
                f"a threshold."
            )

        threshold = self._to_number(
            rule["threshold"],
            (
                f"Threshold for rule "
                f"'{rule_id}'"
            ),
        )

        matching_rows = self._find_matching_rows(
            summary_rows=summary_rows,
            component_name=component_name,
            metric_name=metric_name,
        )

        # A rule without metric_name, such as replica_count,
        # should only be evaluated once per component.
        if metric_name is None:
            matching_rows = (
                self._deduplicate_by_component(
                    matching_rows
                )
            )

        if not matching_rows:
            return [
                {
                    "rule_id": rule_id,
                    "description": description,
                    "component_name": (
                        component_name
                    ),
                    "metric_name": (
                        str(metric_name)
                        if metric_name is not None
                        else ""
                    ),
                    "statistic": statistic,
                    "operator": operator,
                    "threshold": threshold,
                    "actual_value": None,
                    "status": "FAIL",
                    "message": (
                        "No matching summary data "
                        "was found for this rule."
                    ),
                }
            ]

        results: list[dict[str, Any]] = []

        for row in matching_rows:
            actual_raw = row.get(
                statistic
            )

            if actual_raw in (
                None,
                "",
            ):
                results.append(
                    {
                        "rule_id": rule_id,
                        "description": description,
                        "component_name": row.get(
                            "component_name",
                            "",
                        ),
                        "metric_name": row.get(
                            "metric_name",
                            "",
                        ),
                        "statistic": statistic,
                        "operator": operator,
                        "threshold": threshold,
                        "actual_value": None,
                        "status": "FAIL",
                        "message": (
                            f"Statistic '{statistic}' "
                            f"was not available."
                        ),
                    }
                )

                continue

            actual_value = self._to_number(
                actual_raw,
                (
                    f"Statistic '{statistic}' "
                    f"for rule '{rule_id}'"
                ),
            )

            passed = comparison(
                actual_value,
                threshold,
            )

            status = (
                "PASS"
                if passed
                else "FAIL"
            )

            result_component = str(
                row.get(
                    "component_name",
                    "",
                )
            )

            result_metric = str(
                row.get(
                    "metric_name",
                    "",
                )
            )

            message = (
                f"{statistic} = "
                f"{self._format_number(actual_value)}, "
                f"expected {operator} "
                f"{self._format_number(threshold)}"
            )

            results.append(
                {
                    "rule_id": rule_id,
                    "description": description,
                    "component_name": (
                        result_component
                    ),
                    "metric_name": result_metric,
                    "statistic": statistic,
                    "operator": operator,
                    "threshold": threshold,
                    "actual_value": actual_value,
                    "status": status,
                    "message": message,
                }
            )

        return results

    @staticmethod
    def _find_matching_rows(
        summary_rows: list[dict[str, Any]],
        component_name: str,
        metric_name: Any,
    ) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []

        for row in summary_rows:
            if not isinstance(row, dict):
                continue

            row_component = str(
                row.get(
                    "component_name",
                    "",
                )
            )

            if (
                component_name != "*"
                and row_component != component_name
            ):
                continue

            if metric_name is not None:
                row_metric = str(
                    row.get(
                        "metric_name",
                        "",
                    )
                )

                if row_metric != str(metric_name):
                    continue

            matches.append(row)

        return matches

    @staticmethod
    def _deduplicate_by_component(
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Entity summary contains one row per metric.

        For component-level fields such as replica_count,
        keep only one row for each component.
        """

        rows_by_component: dict[
            str,
            dict[str, Any],
        ] = {}

        for row in rows:
            component_name = str(
                row.get(
                    "component_name",
                    "",
                )
            )

            if component_name not in rows_by_component:
                rows_by_component[
                    component_name
                ] = row

        return list(
            rows_by_component.values()
        )

    @staticmethod
    def _to_number(
        value: Any,
        field_description: str,
    ) -> float:
        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise RuleAnalyzerError(
                f"{field_description} must be numeric. "
                f"Received: {value}"
            ) from exc

    @staticmethod
    def _format_number(
        value: float,
    ) -> str:
        if value.is_integer():
            return str(int(value))

        return f"{value:.2f}"