# ADR 0004: Detecting Retroactive Price Changes

## Context
When operational systems back-date an `updated_at` timestamp during a retroactive price correction (Chaos Scenario C1), timestamp-based SCD2 snapshots will not detect the change if the timestamp precedes the snapshot's active window.

## Decision
We maintain timestamp snapshots for normal daily flow, but enforce an automated singular test **`assert_snapshot_matches_source.sql`**.

## Consequences
- Rather than maintaining expensive historical diff engines, the pipeline validates that the active snapshot record matches the current source state.
- Retroactively modified records trigger an immediate pipeline test failure, forcing explicit operational remediation.
