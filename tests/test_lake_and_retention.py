from datetime import date

from pipeline import config, retention
from pipeline.lake import LocalLake, key_date, object_key


def test_object_key_is_hive_partitioned():
    key = object_key("bronze", "2026-10-14", "20261014T101500Z")
    assert key == "bronze/date=2026-10-14/run_20261014T101500Z.parquet"
    assert key_date(key) == "2026-10-14"


def test_expire_lake_deletes_only_old_partitions(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BRONZE_RETENTION_DAYS", 3)
    monkeypatch.setattr(config, "SILVER_RETENTION_DAYS", 14)
    src = tmp_path / "f.parquet"
    src.write_bytes(b"x")
    lake = LocalLake(tmp_path / "lake")
    for layer, day in [("bronze", "2026-10-10"), ("bronze", "2026-10-11"),
                       ("silver", "2026-09-29"), ("silver", "2026-09-30")]:
        lake.upload(src, object_key(layer, day, "r1"))

    deleted = retention.expire_lake(lake, date(2026, 10, 14))

    assert deleted == {"bronze": 1, "silver": 1, "quarantine": 0}
    remaining = sorted(k for k, _ in lake.list("bronze/") + lake.list("silver/"))
    assert remaining == [
        "bronze/date=2026-10-11/run_r1.parquet",
        "silver/date=2026-09-30/run_r1.parquet",
    ]
