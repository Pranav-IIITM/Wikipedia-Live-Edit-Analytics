"""DuckDB transforms: bronze rows -> silver -> gold aggregates, plus Parquet files for the lake."""

import json
from datetime import timezone
from pathlib import Path

import duckdb

from pipeline.rules import ANON_USER_REGEX, BUCKET_MINUTES

SQL_DIR = Path(__file__).parent / "sql"


def new_connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    return con


def _sql(name: str, **params) -> str:
    text = (SQL_DIR / name).read_text(encoding="utf-8")
    for key, value in params.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def _quote(path: Path) -> str:
    return "'" + path.as_posix().replace("'", "''") + "'"


def load_bronze(con, rows: list[dict], workdir: Path) -> None:
    """Creates the bronze table from collected rows (via newline-delimited JSON)."""
    ndjson = workdir / "bronze.ndjson"
    with open(ndjson, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    con.execute(f"""
        CREATE OR REPLACE TABLE bronze AS
        SELECT * FROM read_json({_quote(ndjson)},
            format = 'newline_delimited',
            columns = {{
                'event_id': 'VARCHAR', 'wiki': 'VARCHAR', 'event_time': 'VARCHAR',
                'raw_json': 'VARCHAR', 'ingested_at': 'TIMESTAMPTZ'
            }})
    """)


def build_silver(con) -> None:
    con.execute(_sql("silver.sql", anon_regex=ANON_USER_REGEX.replace("'", "''")))


def build_gold(con) -> None:
    con.execute(_sql("gold.sql", bucket_minutes=BUCKET_MINUTES))


def write_parquet(con, table: str, path: Path) -> int:
    count = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    if count:
        con.execute(f"COPY {table} TO {_quote(path)} (FORMAT parquet, COMPRESSION zstd)")
    return count


def _utc(ts):
    return ts.replace(tzinfo=timezone.utc)


def fetch_page_rows(con) -> list[tuple]:
    rows = con.execute("""
        SELECT wiki, title, bucket_start, edits, human_edits, bot_edits, new_pages,
               bytes_changed, editors
        FROM gold_page_15m
    """).fetchall()
    return [(w, t, _utc(b), *rest) for (w, t, b, *rest) in rows]


def fetch_hourly_rows(con) -> list[tuple]:
    rows = con.execute("""
        SELECT wiki, hour_start, edits, human_edits, bot_edits, anon_edits, new_pages,
               bytes_changed, bytes_added
        FROM gold_wiki_hourly
    """).fetchall()
    return [(w, _utc(h), *rest) for (w, h, *rest) in rows]


def count(con, table: str) -> int:
    return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
