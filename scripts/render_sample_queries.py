"""Render sample queries against the DuckDB warehouse into docs/sample_queries.md."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
QUERIES_DIR = REPO_ROOT / "queries"
DOCS_FILE = REPO_ROOT / "docs" / "sample_queries.md"
DUCKDB_PATH = Path(os.environ.get("DUCKDB_PATH", REPO_ROOT / "data" / "dukastack.duckdb"))


def connect_duckdb(db_path: Path, max_attempts: int = 5) -> duckdb.DuckDBPyConnection:
    """Connect to DuckDB with retry handling in read-only mode."""
    if not db_path.exists():
        raise FileNotFoundError(
            f"DuckDB database not found at {db_path}. Run 'make demo' or 'make build' first."
        )

    for attempt in range(1, max_attempts + 1):
        try:
            con = duckdb.connect(str(db_path), read_only=True)
            con.execute("SET search_path = 'main_marts,main_core,snapshots,raw,main'")
            return con
        except Exception as exc:
            if "lock" in str(exc).lower() and attempt < max_attempts:
                time.sleep(0.5 * attempt)
                continue
            raise


def parse_query_file(file_path: Path) -> tuple[dict[str, str], str]:
    """Extract comment header metadata and SQL content from a query file."""
    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    metadata: dict[str, str] = {
        "question": "",
        "grain": "",
        "notes": "",
    }
    sql_lines: list[str] = []
    notes_lines: list[str] = []
    in_notes = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("-- Question:"):
            metadata["question"] = stripped.replace("-- Question:", "").strip()
            in_notes = False
        elif stripped.startswith("-- Grain:"):
            metadata["grain"] = stripped.replace("-- Grain:", "").strip()
            in_notes = False
        elif stripped.startswith("-- What to look for:"):
            in_notes = True
        elif in_notes and stripped.startswith("--"):
            notes_lines.append(stripped.lstrip("-").strip())
        elif stripped.startswith("--"):
            continue
        else:
            in_notes = False
            sql_lines.append(line)

    metadata["notes"] = "\n".join(f"- {n}" for n in notes_lines if n)
    sql_code = "\n".join(sql_lines).strip()
    return metadata, sql_code


def format_markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    """Format headers and rows into a clean GitHub-flavored markdown table."""
    if not headers:
        return "_No results._\n"

    str_rows = [[str(cell) if cell is not None else "NULL" for cell in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in str_rows:
        for idx, val in enumerate(row):
            widths[idx] = max(widths[idx], len(val))

    header_line = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    separator_line = "| " + " | ".join("-" * widths[i] for i in range(len(headers))) + " |"
    data_lines = [
        "| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(headers))) + " |"
        for row in str_rows
    ]

    return "\n".join([header_line, separator_line] + data_lines)


def main() -> None:
    """Execute all sample queries and write results to docs/sample_queries.md."""
    con = connect_duckdb(DUCKDB_PATH)

    sql_files = sorted(QUERIES_DIR.glob("bq*.sql"))
    if not sql_files:
        print(f"No queries found in {QUERIES_DIR}", file=sys.stderr)
        sys.exit(1)

    sections: list[str] = [
        "# DukaStack Sample Warehouse Queries\n",
        "Automated results executed against `data/dukastack.duckdb`.\n",
        "To re-render these results, run:\n",
        "```bash\nmake queries\n```\n",
        "---\n",
    ]

    for sql_file in sql_files:
        query_id = sql_file.stem.split("_")[0].upper()
        metadata, sql_code = parse_query_file(sql_file)

        print(f"Running {sql_file.name}...")
        cur = con.execute(sql_code)
        headers = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()[:10]

        section_md = [
            f"## {query_id}: {metadata['question'] or sql_file.stem}",
            "",
            f"**Grain:** {metadata['grain'] or 'N/A'}",
            "",
        ]

        if metadata["notes"]:
            section_md.extend(
                [
                    "**What to look for:**",
                    metadata["notes"],
                    "",
                ]
            )

        section_md.extend(
            [
                "```sql",
                sql_code,
                "```",
                "",
                "### Results (Top 10 rows)",
                "",
                format_markdown_table(headers, rows),
                "",
                "---",
                "",
            ]
        )

        sections.append("\n".join(section_md))

    DOCS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DOCS_FILE.write_text("\n".join(sections), encoding="utf-8")
    con.close()
    print(f"Wrote sample query results to {DOCS_FILE}")


if __name__ == "__main__":
    main()
