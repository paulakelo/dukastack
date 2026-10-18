"""Dagster schedule and job definitions for daily pipeline runs.

Provides:
- daily_pipeline_job: runs simulation advancement, raw load, dbt build, and asset checks.
- daily_pipeline_schedule: triggers daily execution at midnight UTC.
"""

from dagster import (
    AssetSelection,
    ScheduleDefinition,
    define_asset_job,
)

daily_pipeline_job = define_asset_job(
    name="daily_pipeline_job",
    selection=AssetSelection.all(),
    description="Daily pipeline: advances simulation, refreshes dbt models, and runs checks.",
)

daily_pipeline_schedule = ScheduleDefinition(
    job=daily_pipeline_job,
    cron_schedule="0 0 * * *",
    description="Daily scheduled execution of the dukastack warehouse pipeline.",
)
