from pathlib import Path
from uuid import uuid4

import pandas as pd

from run import run_pipeline
from src.data_profiler import build_profile_report, count_range_violations
from src.data_transformer import transform_data
from src.data_validator import add_validation_flags, build_validation_report, validate_schema


def test_profile_report_counts_nulls_and_duplicates():
    df = pd.DataFrame(
        {
            "run_id": [1, 1, 2],
            "actual_units": [100, 100, 0],
            "defective_units": [5, 5, 1],
            "efficiency_pct_x": [95.0, 95.0, None],
            "last_maintenance": ["2024-01-01", "2024-01-01", None],
        }
    )

    report = build_profile_report(df)

    assert report["row_count"] == 3
    assert report["column_count"] == 5
    assert report["duplicate_rows"] == 1
    assert report["null_counts"]["efficiency_pct_x"] == 1
    assert report["null_counts"]["last_maintenance"] == 1


def test_range_violations_match_manufacturing_rules():
    df = pd.DataFrame(
        {
            "actual_units": [100, 0, 10],
            "defective_units": [5, 1, 20],
            "efficiency_pct_x": [80.0, 101.0, -2.0],
            "passed": [9, 7, 12],
            "failed": [1, 4, 1],
            "sample_size": [10, 10, 10],
        }
    )

    violations = count_range_violations(df)

    assert violations["actual_units_zero"] == 1
    assert violations["defective_units_above_actual_units"] == 2
    assert violations["efficiency_pct_x_above_100"] == 1
    assert violations["efficiency_pct_x_below_0"] == 1
    assert violations["passed_failed_not_equal_sample_size"] == 2


def test_validator_flags_bad_manufacturing_rows():
    df = pd.DataFrame(
        {
            "run_id": [1, 2, 3],
            "run_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "planned_units": [100, 100, 100],
            "actual_units": [100, 0, 10],
            "defective_units": [5, 1, 20],
            "efficiency_pct_x": [80.0, 101.0, 90.0],
            "operator": ["Operator-1", " ", None],
            "last_maintenance": ["2024-01-01", None, "2024-01-03"],
        }
    )

    validated_df = add_validation_flags(df)
    report = build_validation_report(validated_df)

    assert validated_df["invalid_actual_units_zero"].tolist() == [
        False,
        True,
        False,
    ]
    assert validated_df["invalid_defective_units_above_actual_units"].tolist() == [
        False,
        True,
        True,
    ]
    assert validated_df["invalid_efficiency_above_100"].tolist() == [
        False,
        True,
        False,
    ]
    assert validated_df["missing_last_maintenance"].tolist() == [False, True, False]
    assert validated_df["missing_operator"].tolist() == [False, True, True]
    assert report["valid_row_count"] == 1
    assert report["invalid_row_count"] == 2


def test_validate_schema_requires_core_columns_and_efficiency_column():
    df = pd.DataFrame(
        {
            "run_id": [1],
            "run_date": ["2024-01-01"],
            "planned_units": [100],
            "actual_units": [95],
            "defective_units": [1],
            "operator": ["Operator-1"],
            "last_maintenance": ["2024-01-01"],
            "efficiency_pct_x": [95.0],
        }
    )

    schema_report = validate_schema(df)

    assert schema_report["is_valid"] is True
    assert schema_report["missing_columns"] == []
    assert schema_report["efficiency_columns"] == ["efficiency_pct_x"]


def test_transformer_cleans_readme_issues_and_adds_audit_trail():
    df = pd.DataFrame(
        {
            "run_id": [1, 2, 3],
            "run_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "actual_units": [100, 0, 10],
            "defective_units": [5, 1, 20],
            "efficiency_pct_x": [80.0, 101.0, -2.0],
            "equipment_type": ["CNC Machine", "CNC Machine", "Robot Arm"],
            "last_maintenance": ["2024-01-01", None, "2024-03-01"],
            "operator": [" Operator-1 ", "Operator-2", "Operator-3"],
            "invalid_efficiency_above_100": [False, True, False],
            "invalid_defective_units_above_actual_units": [False, True, True],
            "invalid_actual_units_zero": [False, True, False],
            "missing_last_maintenance": [False, True, False],
            "missing_operator": [False, False, False],
        }
    )

    transformed_df = transform_data(df)

    assert transformed_df["operator"].tolist() == [
        "Operator-1",
        "Operator-2",
        "Operator-3",
    ]
    assert transformed_df["efficiency_pct_x"].tolist() == [80.0, 100.0, 0.0]
    assert transformed_df["defective_units"].tolist() == [5, 0, 10]
    assert transformed_df["defect_rate"].tolist() == [0.05, 0.0, 1.0]
    assert pd.notna(transformed_df.loc[1, "last_maintenance"])
    assert "filled_last_maintenance" in transformed_df.loc[1, "pipeline_audit_trail"]
    assert "recalculated_defect_rate" in transformed_df.loc[0, "pipeline_audit_trail"]


def test_run_pipeline_creates_processed_file():
    test_output_dir = Path("test-output")
    test_output_dir.mkdir(exist_ok=True)
    run_id = uuid4().hex
    input_path = test_output_dir / f"raw-data-{run_id}.csv"
    output_path = test_output_dir / f"processed-data-{run_id}.csv"

    pd.DataFrame(
        {
            "run_id": [1, 2],
            "run_date": ["2024-01-01", "2024-01-02"],
            "planned_units": [100, 100],
            "actual_units": [100, 0],
            "defective_units": [5, 1],
            "efficiency_pct_x": [80.0, 101.0],
            "operator": ["Operator-1", "Operator-2"],
            "equipment_type": ["CNC Machine", "CNC Machine"],
            "last_maintenance": ["2024-01-01", None],
        }
    ).to_csv(input_path, index=False)

    result = run_pipeline(input_path=input_path, output_path=output_path)
    processed_df = pd.read_csv(output_path)

    assert output_path.exists()
    assert result["processed_row_count"] == 2
    assert result["validation_report"]["invalid_row_count"] == 1
    assert processed_df["efficiency_pct_x"].max() == 100.0
    assert processed_df["last_maintenance"].isna().sum() == 0
