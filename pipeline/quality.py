"""Data-quality gates. A failed critical check stops the run before anything is published."""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from pipeline.collect import CollectResult


@dataclass
class Check:
    name: str
    passed: bool
    detail: str
    critical: bool = True

    def as_dict(self) -> dict:
        return asdict(self)


class QualityError(Exception):
    def __init__(self, checks: list[Check]):
        self.checks = checks
        failed = [f"{c.name}: {c.detail}" for c in checks if c.critical and not c.passed]
        super().__init__("quality checks failed: " + "; ".join(failed))


def run_checks(con, collected: CollectResult, now: datetime) -> list[Check]:
    checks: list[Check] = []
    bronze = con.execute("SELECT count(*) FROM bronze").fetchone()[0]
    silver = con.execute("SELECT count(*) FROM silver").fetchone()[0]
    quarantined = con.execute("SELECT count(*) FROM quarantine").fetchone()[0]

    dupes = con.execute(
        "SELECT count(*) FROM (SELECT event_id FROM silver GROUP BY 1 HAVING count(*) > 1)"
    ).fetchone()[0]
    checks.append(Check("unique_event_ids", dupes == 0, f"{dupes} duplicated event_id(s) in silver"))

    rate = quarantined / bronze if bronze else 0.0
    checks.append(Check(
        "quarantine_rate",
        bronze < 50 or rate <= 0.02,
        f"{quarantined}/{bronze} rows quarantined ({rate:.1%}, limit 2%)",
    ))

    # English Wikipedia always has article edits; a big stream with nothing kept means a broken filter.
    checks.append(Check(
        "events_kept",
        collected.events_seen < 5000 or collected.events_kept > 0,
        f"kept {collected.events_kept} of {collected.events_seen} events",
    ))

    future = 0
    if silver:
        future = con.execute(
            "SELECT count(*) FROM silver WHERE event_time > ?::TIMESTAMPTZ",
            [now + timedelta(minutes=5)],
        ).fetchone()[0]
    checks.append(Check("no_future_events", future == 0, f"{future} event(s) dated in the future"))

    checks.append(Check(
        "caught_up",
        collected.caught_up,
        "reached live edge of the stream" if collected.caught_up
        else "time budget ran out first; next run resumes from checkpoint",
        critical=False,
    ))
    return checks


def enforce(checks: list[Check]) -> None:
    if any(c.critical and not c.passed for c in checks):
        raise QualityError(checks)
