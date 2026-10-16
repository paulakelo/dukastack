# ADR 0002: Timestamp Snapshot Strategy for SCD Type 2

## Context
Tracking changes to customer loyalty tiers and product prices requires creating Slowly Changing Dimension Type 2 (SCD2) history from source tables that only store current state.

## Considered Alternatives
1. `check` strategy (compares hash of tracked columns)
2. `timestamp` strategy using `updated_at`

## Decision
We select the **`timestamp` strategy** relying on `updated_at` from the operational store.

## Consequences
- Clean alignment between simulated source event timestamps and snapshot validity ranges (`dbt_valid_from`, `dbt_valid_to`).
- Known limitation: If a daily run is skipped and multiple changes occur within that window, intermediate states are lost. This trade-off is accepted for v1 and monitored via Dagster freshness checks.
