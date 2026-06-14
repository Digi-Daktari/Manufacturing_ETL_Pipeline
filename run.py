from __future__ import annotations

from pathlib import Path
from typing import Any

from config import PROCESSED_DATA_PATH, logger
from src.data_profiler import PROFILE_REPORT_PATH, profile_raw_data
from src.data_transformer import save_processed_data, transform_data
from src.data_validator import VALIDATION_REPORT_PATH, validate_raw_data


def run_pipeline(
    input_path: str | Path | None = None,
    output_path: str | Path = PROCESSED_DATA_PATH,
) -> dict[str, Any]:
    logger.info("Starting manufacturing ETL pipeline")

    profile_report = profile_raw_data(
        input_path=input_path,
        report_path=PROFILE_REPORT_PATH,
    )
    logger.info(
        "Profile complete: %s rows, %s columns, %s duplicate rows",
        profile_report["row_count"],
        profile_report["column_count"],
        profile_report["duplicate_rows"],
    )

    validated_df, validation_report = validate_raw_data(
        input_path=input_path,
        report_path=VALIDATION_REPORT_PATH,
    )
    logger.info(
        "Validation complete: %s valid rows, %s invalid rows",
        validation_report["valid_row_count"],
        validation_report["invalid_row_count"],
    )

    transformed_df = transform_data(validated_df)
    processed_path = save_processed_data(transformed_df, output_path)

    logger.info("Manufacturing ETL pipeline complete")
    logger.info("Processed data: %s", processed_path)
    logger.info("Profile report: %s", PROFILE_REPORT_PATH)
    logger.info("Validation report: %s", VALIDATION_REPORT_PATH)

    return {
        "profile_report": profile_report,
        "validation_report": validation_report,
        "processed_path": processed_path,
        "processed_row_count": int(len(transformed_df)),
        "processed_column_count": int(len(transformed_df.columns)),
    }


def main() -> None:
    run_pipeline()


if __name__ == "__main__":
    main()
