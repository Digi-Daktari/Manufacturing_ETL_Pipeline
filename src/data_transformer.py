from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from config import PROCESSED_DATA_PATH, logger
from src.data_validator import validate_raw_data


DATE_COLUMNS = [
    "run_date",
    "check_date",
    "install_date",
    "last_maintenance",
    "next_maintenance",
]

INTEGER_COLUMNS = [
    "run_id",
    "plant_id",
    "product_id",
    "planned_units",
    "actual_units",
    "defective_units",
    "check_id",
    "sample_size",
    "passed",
    "failed",
    "equipment_id",
    "capacity_units",
    "employees_count",
    "opened_year",
    "lead_time_days",
]

FLOAT_COLUMNS = [
    "efficiency_pct_x",
    "efficiency_pct_y",
    "downtime_mins",
    "unit_cost",
    "target_price",
    "weight_kg",
    "defect_rate",
    "efficiency_rank",
]

TEXT_COLUMNS = [
    "shift",
    "operator",
    "inspector",
    "defect_type",
    "severity",
    "action_taken",
    "equipment_name",
    "equipment_type",
    "manufacturer",
    "status",
    "plant_name",
    "city",
    "country",
    "plant_type",
    "manager",
    "product_code",
    "product_name",
    "category",
]


def get_efficiency_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in df.columns if column.startswith("efficiency_pct")]


def correct_data_types(df: pd.DataFrame) -> pd.DataFrame:
    transformed_df = df.copy()

    for column in DATE_COLUMNS:
        if column in transformed_df.columns:
            transformed_df[column] = pd.to_datetime(
                transformed_df[column],
                errors="coerce",
            )

    for column in INTEGER_COLUMNS:
        if column in transformed_df.columns:
            transformed_df[column] = pd.to_numeric(
                transformed_df[column],
                errors="coerce",
            ).astype("Int64")

    for column in FLOAT_COLUMNS:
        if column in transformed_df.columns:
            transformed_df[column] = pd.to_numeric(
                transformed_df[column],
                errors="coerce",
            )

    for column in TEXT_COLUMNS:
        if column in transformed_df.columns:
            transformed_df[column] = (
                transformed_df[column].astype("string").str.strip()
            )

    return transformed_df


def _median_timestamp(series: pd.Series) -> pd.Timestamp | None:
    valid_dates = series.dropna()
    if valid_dates.empty:
        return None

    numeric_dates = valid_dates.astype("int64")
    return pd.to_datetime(int(numeric_dates.median()))


def fill_missing_maintenance_dates(df: pd.DataFrame) -> pd.DataFrame:
    transformed_df = df.copy()
    if "last_maintenance" not in transformed_df.columns:
        return transformed_df

    if "equipment_type" in transformed_df.columns:
        group_medians = transformed_df.groupby("equipment_type")[
            "last_maintenance"
        ].transform(_median_timestamp)
        transformed_df["last_maintenance"] = transformed_df[
            "last_maintenance"
        ].fillna(group_medians)

    overall_median = _median_timestamp(transformed_df["last_maintenance"])
    if pd.notna(overall_median):
        transformed_df["last_maintenance"] = transformed_df[
            "last_maintenance"
        ].fillna(overall_median)

    return transformed_df


def cap_efficiency_values(df: pd.DataFrame) -> pd.DataFrame:
    transformed_df = df.copy()
    for column in get_efficiency_columns(transformed_df):
        transformed_df[column] = transformed_df[column].clip(lower=0, upper=100)
    return transformed_df


def correct_unit_violations(df: pd.DataFrame) -> pd.DataFrame:
    transformed_df = df.copy()
    if {"defective_units", "actual_units"}.issubset(transformed_df.columns):
        transformed_df["defective_units"] = transformed_df[
            ["defective_units", "actual_units"]
        ].min(axis=1)

    return transformed_df


def add_defect_rate(df: pd.DataFrame) -> pd.DataFrame:
    transformed_df = df.copy()
    if {"defective_units", "actual_units"}.issubset(transformed_df.columns):
        actual_units = transformed_df["actual_units"].replace(0, np.nan)
        transformed_df["defect_rate"] = (
            transformed_df["defective_units"] / actual_units
        ).fillna(0.0)

    return transformed_df


def add_pipeline_audit_trail(df: pd.DataFrame) -> pd.DataFrame:
    transformed_df = df.copy()

    audit_columns = {
        "invalid_efficiency_above_100": "capped_efficiency_pct",
        "invalid_defective_units_above_actual_units": "capped_defective_units",
        "invalid_actual_units_zero": "set_defect_rate_to_zero",
        "missing_last_maintenance": "filled_last_maintenance",
        "missing_operator": "flagged_missing_operator",
    }

    def build_audit_note(row: pd.Series) -> str:
        actions = [
            action
            for column, action in audit_columns.items()
            if bool(row.get(column, False))
        ]
        actions.append("recalculated_defect_rate")
        return "; ".join(actions)

    transformed_df["pipeline_audit_trail"] = transformed_df.apply(
        build_audit_note,
        axis=1,
    )
    return transformed_df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    transformed_df = correct_data_types(df)
    transformed_df = fill_missing_maintenance_dates(transformed_df)
    transformed_df = cap_efficiency_values(transformed_df)
    transformed_df = correct_unit_violations(transformed_df)
    transformed_df = add_defect_rate(transformed_df)
    transformed_df = add_pipeline_audit_trail(transformed_df)
    return transformed_df


def save_processed_data(
    df: pd.DataFrame,
    path: str | Path = PROCESSED_DATA_PATH,
) -> Path:
    processed_path = Path(path)
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(processed_path, index=False)
    logger.info("Processed data saved to %s", processed_path)
    return processed_path


def transform_raw_data(
    input_path: str | Path | None = None,
    output_path: str | Path = PROCESSED_DATA_PATH,
) -> pd.DataFrame:
    validated_df, _ = validate_raw_data(input_path)
    transformed_df = transform_data(validated_df)
    save_processed_data(transformed_df, output_path)
    return transformed_df


if __name__ == "__main__":
    transform_raw_data()
