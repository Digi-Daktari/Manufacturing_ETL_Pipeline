-- PrecisionCraft Industries - Manufacturing ETL Pipeline
-- Database: PostgreSQL / Supabase
-- Run this script in your SQL editor before loading processed-data.csv.
-- This script assumes your learner_03 schema already exists.
-- If your assigned schema has a different name, replace learner_03 everywhere.

-- Refresh views so older broken definitions do not stay in the database.
drop view if exists learner_03.manufacturing_etl_daily_production;
drop view if exists learner_03.manufacturing_etl_quality_summary;

-- Use this only if you want to completely rebuild the table:
-- drop table if exists learner_03.manufacturing_etl_pipeline;

create table if not exists learner_03.manufacturing_etl_pipeline (
    etl_row_id bigserial primary key,

    run_id integer not null,
    plant_id integer,
    product_id integer,
    run_date date,
    shift text,
    planned_units integer,
    actual_units integer,
    defective_units integer,
    efficiency_pct_x numeric(6, 2),
    downtime_mins numeric(10, 2),
    operator text,

    check_id integer,
    check_date date,
    inspector text,
    sample_size integer,
    passed integer,
    failed integer,
    defect_type text,
    severity text,
    action_taken text,

    equipment_id integer,
    equipment_name text,
    equipment_type text,
    manufacturer text,
    install_date date,
    last_maintenance timestamp,
    next_maintenance date,
    status text,
    efficiency_pct_y numeric(6, 2),

    plant_name text,
    city text,
    country text,
    plant_type text,
    capacity_units integer,
    employees_count integer,
    manager text,
    opened_year integer,
    is_active_x boolean,

    product_code text,
    product_name text,
    category text,
    unit_cost numeric(12, 2),
    target_price numeric(12, 2),
    weight_kg numeric(12, 2),
    lead_time_days integer,
    is_active_y boolean,

    defect_rate numeric(12, 8),
    efficiency_rank numeric(10, 2),

    invalid_actual_units_zero boolean default false,
    invalid_defective_units_above_actual_units boolean default false,
    invalid_efficiency_above_100 boolean default false,
    missing_last_maintenance boolean default false,
    missing_operator boolean default false,
    is_valid_row boolean default true,
    validation_issues text,
    pipeline_audit_trail text,

    loaded_at timestamp default current_timestamp,

    constraint chk_actual_units_nonnegative
        check (actual_units is null or actual_units >= 0),
    constraint chk_defective_units_nonnegative
        check (defective_units is null or defective_units >= 0),
    constraint chk_defective_units_not_above_actual
        check (
            defective_units is null
            or actual_units is null
            or defective_units <= actual_units
        ),
    constraint chk_efficiency_pct_x_range
        check (
            efficiency_pct_x is null
            or efficiency_pct_x between 0 and 100
        ),
    constraint chk_efficiency_pct_y_range
        check (
            efficiency_pct_y is null
            or efficiency_pct_y between 0 and 100
        ),
    constraint chk_defect_rate_range
        check (
            defect_rate is null
            or defect_rate between 0 and 1
        )
);

create index if not exists idx_manufacturing_etl_run_id
    on learner_03.manufacturing_etl_pipeline (run_id);

create index if not exists idx_manufacturing_etl_run_date
    on learner_03.manufacturing_etl_pipeline (run_date);

create index if not exists idx_manufacturing_etl_plant_product
    on learner_03.manufacturing_etl_pipeline (plant_id, product_id);

create index if not exists idx_manufacturing_etl_equipment_type
    on learner_03.manufacturing_etl_pipeline (equipment_type);

create index if not exists idx_manufacturing_etl_valid_row
    on learner_03.manufacturing_etl_pipeline (is_valid_row);

create or replace view learner_03.manufacturing_etl_quality_summary as
select
    count(*) as total_rows,
    count(*) filter (where is_valid_row) as valid_rows,
    count(*) filter (where not is_valid_row) as invalid_rows,
    count(*) filter (where missing_last_maintenance) as rows_filled_last_maintenance,
    count(*) filter (where invalid_actual_units_zero) as rows_actual_units_zero,
    count(*) filter (
        where invalid_defective_units_above_actual_units
    ) as rows_defective_units_above_actual_units,
    count(*) filter (where invalid_efficiency_above_100) as rows_efficiency_above_100,
    round(avg(defect_rate), 6) as avg_defect_rate,
    round(avg(efficiency_pct_x), 2) as avg_run_efficiency_pct,
    round(avg(efficiency_pct_y), 2) as avg_equipment_efficiency_pct
from learner_03.manufacturing_etl_pipeline;

create or replace view learner_03.manufacturing_etl_daily_production as
select
    run_date,
    plant_id,
    plant_name,
    product_id,
    product_name,
    sum(planned_units) as total_planned_units,
    sum(actual_units) as total_actual_units,
    sum(defective_units) as total_defective_units,
    round(avg(defect_rate), 6) as avg_defect_rate,
    round(avg(efficiency_pct_x), 2) as avg_efficiency_pct
from learner_03.manufacturing_etl_pipeline
group by
    run_date,
    plant_id,
    plant_name,
    product_id,
    product_name;

-- Quick checks to run after loading processed-data.csv:
select * from learner_03.manufacturing_etl_quality_summary;

select
    pipeline_audit_trail,
    count(*) as row_count
from learner_03.manufacturing_etl_pipeline
group by pipeline_audit_trail
order by row_count desc;

select
    equipment_type,
    count(*) as row_count,
    round(avg(defect_rate), 6) as avg_defect_rate,
    round(avg(efficiency_pct_y), 2) as avg_equipment_efficiency_pct
from learner_03.manufacturing_etl_pipeline
group by equipment_type
order by avg_defect_rate desc nulls last;
