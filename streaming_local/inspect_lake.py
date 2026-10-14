"""Prints row counts and a sample from the local Delta tables (run on the host).

    python -m streaming_local.inspect_lake
"""

from pathlib import Path

import duckdb

LAKE = Path(__file__).parent / "data"
TABLES = ["bronze", "silver", "quarantine", "gold/page_activity_15m", "gold/wiki_activity_hourly", "gold/trending_30m"]


def main():
    con = duckdb.connect()
    con.execute("INSTALL delta; LOAD delta;")
    for name in TABLES:
        path = LAKE / name
        if not (path / "_delta_log").exists():
            print(f"{name:<28} (not created yet)")
            continue
        n = con.execute(f"SELECT count(*) FROM delta_scan('{path.as_posix()}')").fetchone()[0]
        print(f"{name:<28} {n:>8} rows")

    trending = LAKE / "gold/trending_30m"
    if (trending / "_delta_log").exists():
        print("\nlatest trending window:")
        rows = con.execute(f"""
            SELECT CAST(window_end AS VARCHAR), wiki, title, human_edits, editors
            FROM delta_scan('{trending.as_posix()}')
            QUALIFY window_end = max(window_end) OVER ()
            ORDER BY editors DESC, human_edits DESC LIMIT 10
        """).fetchall()
        for r in rows:
            print("  ", *r)


if __name__ == "__main__":
    main()
