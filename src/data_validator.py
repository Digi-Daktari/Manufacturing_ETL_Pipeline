from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from config import PROCESSED_DATA_DIR, logger
from src.data_profiler import load_raw_data


VALIDATION_REPORT_PATH = PROCESSED_DATA_DIR / "validation-report.json"

REQUIRED_COLUMNS = [
    "run_id",
    "run_date",
    "planned_units",
    "actual_units",
    "defective_units",
    "operator",
    "last_maintenance",
]


def get_efficiency_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in df.columns if column.startswith("efficiency_pct")]


def validate_schema(df: pd.DataFrame) -> dict[str, Any]:
    efficiency_columns = get_efficiency_columns(df)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]

    return {
        "is_valid": not missing_columns and bool(efficiency_columns),
        "missing_columns": missing_columns,
        "efficiency_columns": efficiency_columns,
    }


def add_validation_flags(df: pd.DataFrame) -> pd.DataFrame:
    validated_df = df.copy()
    efficiency_columns = get_efficiency_columns(validated_df)

    validated_df["invalid_actual_units_zero"] = False
    if "actual_units" in validated_df.columns:
        validated_df["invalid_actual_units_zero"] = validated_df["actual_units"] == 0

    validated_df["invalid_defective_units_above_actual_units"] = False
    if {"defective_units", "actual_units"}.issubset(validated_df.columns):
        validated_df["invalid_defective_units_above_actual_units"] = (
            validated_df["defective_units"] > validated_df["actual_units"]
        )

    validated_df["invalid_efficiency_above_100"] = False
    for column in efficiency_columns:
        validated_df["invalid_efficiency_above_100"] = (
            validated_df["invalid_efficiency_above_100"]
            | (validated_df[column] > 100)
        )

    validated_df["missing_last_maintenance"] = False
    if "last_maintenance" in validated_df.columns:
        validated_df["missing_last_maintenance"] = validated_df[
            "last_maintenance"
        ].isna()

    validated_df["missing_operator"] = False
    if "operator" in validated_df.columns:
        operator_text = validated_df["operator"].astype("string").str.strip()
        validated_df["missing_operator"] = operator_text.isna() | (operator_text == "")

    issue_columns = [
        "invalid_efficiency_above_100",
        "invalid_defective_units_above_actual_units",
        "invalid_actual_units_zero",
        "missing_last_maintenance",
        "missing_operator",
    ]
    validated_df["is_valid_row"] = ~validated_df[issue_columns].any(axis=1)
    validated_df["validation_issues"] = validated_df.apply(
        _format_validation_issues,
        axis=1,
    )

    return validated_df


def _format_validation_issues(row: pd.Series) -> str:
    issue_names = {
        "invalid_efficiency_above_100": "efficiency_pct_above_100",
        "invalid_defective_units_above_actual_units": (
            "defective_units_above_actual_units"
        ),
        "invalid_actual_units_zero": "actual_units_zero",
        "missing_last_maintenance": "missing_last_maintenance",
        "missing_operator": "missing_operator",
    }
    issues = [
        issue_name
        for column, issue_name in issue_names.items()
        if bool(row.get(column, False))
    ]
    return "; ".join(issues)


def build_validation_report(validated_df: pd.DataFrame) -> dict[str, Any]:
    issue_columns = [
        column
        for column in validated_df.columns
        if column.startswith("invalid_") or column.startswith("missing_")
    ]
    issue_counts = {
        column: int(validated_df[column].sum())
        for column in issue_columns
        if pd.api.types.is_bool_dtype(validated_df[column])
    }
    invalid_row_count = int((~validated_df["is_valid_row"]).sum())

    return {
        "row_count": int(len(validated_df)),
        "valid_row_count": int(validated_df["is_valid_row"].sum()),
        "invalid_row_count": invalid_row_count,
        "issue_counts": issue_counts,
    }


def save_validation_report(
    report: dict[str, Any],
    path: str | Path = VALIDATION_REPORT_PATH,
) -> Path:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Validation report saved to %s", report_path)
    return report_path


def validate_data(
    df: pd.DataFrame,
    report_path: str | Path | None = VALIDATION_REPORT_PATH,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    schema_report = validate_schema(df)
    if not schema_report["is_valid"]:
        logger.warning("Schema validation warning: %s", schema_report)

    validated_df = add_validation_flags(df)
    report = build_validation_report(validated_df)
    report["schema"] = schema_report

    if report_path is not None:
        save_validation_report(report, report_path)

    return validated_df, report


def validate_raw_data(
    input_path: str | Path | None = None,
    report_path: str | Path | None = VALIDATION_REPORT_PATH,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    df = load_raw_data(input_path)
    return validate_data(df, report_path)


if __name__ == "__main__":
    validate_raw_data()
