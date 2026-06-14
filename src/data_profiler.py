from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from config import DATA_DIR, PROCESSED_DATA_DIR, RAW_DATA_PATH, logger


PROFILE_REPORT_PATH = PROCESSED_DATA_DIR / "profile-report.json"


def resolve_raw_data_path(path: str | Path | None = None) -> Path:
    """Find the raw data file while the project is still being wired up."""
    if path is not None:
        return Path(path)

    if RAW_DATA_PATH.exists():
        return RAW_DATA_PATH

    flat_data_path = DATA_DIR / "raw-data.csv"
    if flat_data_path.exists():
        return flat_data_path

    return RAW_DATA_PATH


def load_raw_data(path: str | Path | None = None) -> pd.DataFrame:
    raw_path = resolve_raw_data_path(path)
    logger.info("Loading raw data from %s", raw_path)
    return pd.read_csv(raw_path)


def _percent(part: int | float, total: int | float) -> float:
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


def _series_counts(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.items()}


def count_numeric_outliers(df: pd.DataFrame) -> dict[str, int]:
    outlier_counts: dict[str, int] = {}
    numeric_df = df.select_dtypes(include="number")

    for column in numeric_df.columns:
        values = numeric_df[column].dropna()
        if values.empty:
            outlier_counts[column] = 0
            continue

        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1

        if iqr == 0:
            outlier_counts[column] = 0
            continue

        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)
        outlier_counts[column] = int(
            ((values < lower_bound) | (values > upper_bound)).sum()
        )

    return outlier_counts


def count_range_violations(df: pd.DataFrame) -> dict[str, int]:
    violations: dict[str, int] = {}

    efficiency_columns = [
        column for column in df.columns if column.startswith("efficiency_pct")
    ]
    for column in efficiency_columns:
        violations[f"{column}_below_0"] = int((df[column] < 0).sum())
        violations[f"{column}_above_100"] = int((df[column] > 100).sum())

    if "actual_units" in df.columns:
        violations["actual_units_zero"] = int((df["actual_units"] == 0).sum())
        violations["actual_units_negative"] = int((df["actual_units"] < 0).sum())

    if {"defective_units", "actual_units"}.issubset(df.columns):
        violations["defective_units_above_actual_units"] = int(
            (df["defective_units"] > df["actual_units"]).sum()
        )

    if {"passed", "failed", "sample_size"}.issubset(df.columns):
        violations["passed_failed_not_equal_sample_size"] = int(
            ((df["passed"] + df["failed"]) != df["sample_size"]).sum()
        )
        violations["passed_above_sample_size"] = int(
            (df["passed"] > df["sample_size"]).sum()
        )
        violations["failed_above_sample_size"] = int(
            (df["failed"] > df["sample_size"]).sum()
        )

    nonnegative_columns = [
        "planned_units",
        "defective_units",
        "downtime_mins",
        "sample_size",
        "passed",
        "failed",
        "capacity_units",
        "employees_count",
        "unit_cost",
        "target_price",
        "weight_kg",
        "lead_time_days",
        "defect_rate",
    ]
    for column in nonnegative_columns:
        if column in df.columns:
            violations[f"{column}_negative"] = int((df[column] < 0).sum())

    date_columns = [
        "run_date",
        "check_date",
        "install_date",
        "last_maintenance",
        "next_maintenance",
    ]
    for column in date_columns:
        if column in df.columns:
            parsed_dates = pd.to_datetime(df[column], errors="coerce")
            violations[f"{column}_invalid_date"] = int(
                parsed_dates.isna().sum() - df[column].isna().sum()
            )

    return violations


def summarize_categorical_columns(df: pd.DataFrame, limit: int = 10) -> dict[str, Any]:
    categorical_summary: dict[str, Any] = {}
    categorical_df = df.select_dtypes(exclude="number")

    for column in categorical_df.columns:
        value_counts = categorical_df[column].value_counts(dropna=False).head(limit)
        categorical_summary[column] = {
            "unique_count": int(categorical_df[column].nunique(dropna=True)),
            "top_values": _series_counts(value_counts),
        }

    return categorical_summary


def build_profile_report(df: pd.DataFrame) -> dict[str, Any]:
    row_count = len(df)
    duplicate_count = int(df.duplicated().sum())
    null_counts = df.isna().sum()
    null_percent = (df.isna().mean() * 100).round(2)

    return {
        "row_count": int(row_count),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
        "duplicate_rows": duplicate_count,
        "duplicate_percent": _percent(duplicate_count, row_count),
        "null_counts": _series_counts(null_counts),
        "null_percent": {
            str(column): float(value) for column, value in null_percent.items()
        },
        "numeric_summary": df.describe(include="number").round(2).to_dict(),
        "categorical_summary": summarize_categorical_columns(df),
        "outlier_counts": count_numeric_outliers(df),
        "range_violations": count_range_violations(df),
    }


def save_profile_report(
    report: dict[str, Any],
    path: str | Path = PROFILE_REPORT_PATH,
) -> Path:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info("Profile report saved to %s", report_path)
    return report_path


def profile_raw_data(
    input_path: str | Path | None = None,
    report_path: str | Path | None = PROFILE_REPORT_PATH,
) -> dict[str, Any]:
    df = load_raw_data(input_path)
    report = build_profile_report(df)

    if report_path is not None:
        save_profile_report(report, report_path)

    return report


if __name__ == "__main__":
    profile_raw_data()
