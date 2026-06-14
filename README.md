# Manufacturing ETL Pipeline

Python ETL project for cleaning and validating messy manufacturing operations data from PrecisionCraft Industries. The pipeline profiles raw production, quality, equipment, plant, and product records, applies business-rule validation, transforms the data into an analytics-ready CSV, and includes SQL objects for loading the result into PostgreSQL/Supabase.

## Why This Project Matters

Manufacturing data often contains operational issues that can break reporting: efficiency values above 100%, defective units greater than actual output, missing maintenance dates, inconsistent operators, duplicate rows, and invalid dates. This project demonstrates how I would build a reliable data engineering workflow that makes those issues visible, corrects what can be corrected, and preserves an audit trail.

## Tech Stack

- Python, pandas, NumPy
- pytest for automated testing
- PostgreSQL/Supabase SQL
- python-dotenv for environment configuration
- Structured JSON profiling and validation reports

## Pipeline Flow

1. **Profile** raw data and generate `data/processed/profile-report.json`
2. **Validate** schema and business rules, then generate `data/processed/validation-report.json`
3. **Transform** data types, maintenance dates, efficiency values, unit counts, and defect rates
4. **Load** cleaned output to `data/processed/processed-data.csv`
5. **Analyze** with PostgreSQL table definitions, constraints, indexes, and summary views in `sql/man-etl-pipeline.sql`

## Key Features

- Data quality profiling for nulls, duplicates, outliers, categorical distributions, and range violations
- Row-level validation flags for manufacturing-specific rules
- Cleaning logic for dates, numeric columns, text fields, efficiency caps, and defective unit corrections
- Derived `defect_rate` metric for production quality analysis
- `pipeline_audit_trail` column showing what transformation actions were applied to each row
- PostgreSQL constraints and summary views for downstream reporting
- Unit tests covering profiling, validation, transformation, and full pipeline execution

## Project Structure

```text
.
├── data/
│   ├── raw-data.csv
│   └── processed/
│       ├── processed-data.csv
│       ├── profile-report.json
│       └── validation-report.json
├── src/
│   ├── data_profiler.py
│   ├── data_validator.py
│   └── data_transformer.py
├── sql/
│   └── man-etl-pipeline.sql
├── tests/
│   └── test_man_etl_pipeline.py
├── config.py
├── run.py
└── requirements.txt
```

## How To Run

```bash
python -m venv man-ETL-env
man-ETL-env\Scripts\activate
pip install -r requirements.txt
python run.py
```

Run the test suite:

```bash
pytest
```

## Outputs

- `data/processed/processed-data.csv`: cleaned analytics-ready dataset
- `data/processed/profile-report.json`: raw data quality profile
- `data/processed/validation-report.json`: validation summary and issue counts
- `sql/man-etl-pipeline.sql`: PostgreSQL table, constraints, indexes, views, and quick-check queries

## What This Demonstrates

This project shows practical data engineering skills: data profiling, validation design, transformation logic, test coverage, reproducible pipeline execution, and SQL modeling for analytics. It is intentionally built to reflect real-world production data problems, not just a clean demo dataset.
