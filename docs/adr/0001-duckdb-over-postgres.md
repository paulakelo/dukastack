# ADR 0001: Embedded DuckDB Over Client-Server Postgres

## Context
dukastack needs a relational OLAP storage and execution engine to run dbt models, snapshots, and tests locally and in continuous integration (GitHub Actions).

## Considered Alternatives
1. PostgreSQL (client-server instance)
2. SQLite (embedded OLTP)
3. DuckDB (embedded columnar OLAP)

## Decision
We select **DuckDB** using `dbt-duckdb`.

## Consequences
- **Zero Cost & Zero Infrastructure**: Entire warehouse runs in a single `.duckdb` file without background daemon processes or Docker containers.
- **Fast Columnar Analytics**: Vectorized execution delivers sub-second analytical queries and aggregations.
- **Reproducible CI**: GitHub Actions workflows run without external service dependencies, keeping build times under 2 minutes.
