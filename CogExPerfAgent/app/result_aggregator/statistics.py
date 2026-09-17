import math
from statistics import fmean
from typing import Any


class StatisticsError(Exception):
    """Raised when statistics cannot be calculated."""


class StatisticsCalculator:
    """Utility methods for summary statistics."""

    @staticmethod
    def is_number(value: Any) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )

    @classmethod
    def summarize(
        cls,
        values: list[float],
    ) -> dict[str, int | float | None]:
        valid_values = [
            float(value)
            for value in values
            if cls.is_number(value)
        ]

        if not valid_values:
            return {
                "sample_count": 0,
                "average": None,
                "minimum": None,
                "maximum": None,
                "p50": None,
                "p90": None,
                "p95": None,
                "p99": None,
            }

        return {
            "sample_count": len(valid_values),
            "average": cls.round_value(
                fmean(valid_values)
            ),
            "minimum": cls.round_value(
                min(valid_values)
            ),
            "maximum": cls.round_value(
                max(valid_values)
            ),
            "p50": cls.round_value(
                cls.percentile(valid_values, 50)
            ),
            "p90": cls.round_value(
                cls.percentile(valid_values, 90)
            ),
            "p95": cls.round_value(
                cls.percentile(valid_values, 95)
            ),
            "p99": cls.round_value(
                cls.percentile(valid_values, 99)
            ),
        }

    @staticmethod
    def percentile(
        values: list[float],
        percentile_value: float,
    ) -> float:
        if not values:
            raise StatisticsError(
                "Cannot calculate percentile from an empty list."
            )

        sorted_values = sorted(values)

        if len(sorted_values) == 1:
            return sorted_values[0]

        position = (
            len(sorted_values) - 1
        ) * percentile_value / 100

        lower_index = math.floor(position)
        upper_index = math.ceil(position)

        if lower_index == upper_index:
            return sorted_values[lower_index]

        lower_value = sorted_values[lower_index]
        upper_value = sorted_values[upper_index]
        fraction = position - lower_index

        return lower_value + (
            upper_value - lower_value
        ) * fraction

    @classmethod
    def combine(
        cls,
        values: list[float],
        method: str,
    ) -> float | None:
        valid_values = [
            float(value)
            for value in values
            if cls.is_number(value)
        ]

        if not valid_values:
            return None

        normalized_method = method.lower()

        if normalized_method == "sum":
            result = sum(valid_values)

        elif normalized_method == "avg":
            result = fmean(valid_values)

        elif normalized_method == "max":
            result = max(valid_values)

        elif normalized_method == "min":
            result = min(valid_values)

        else:
            raise StatisticsError(
                f"Unsupported aggregation method: {method}"
            )

        return cls.round_value(result)

    @staticmethod
    def round_value(value: float) -> float:
        return round(float(value), 2)