"""Runtime settings, read from environment variables (see .env.example)."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


USER_AGENT = os.getenv(
    "WIKIPULSE_USER_AGENT",
    "WikiPulse/0.1 (https://github.com/Pranav-IIITM/Wikipedia-Live-Edit-Analytics)",
)

# Postgres connection string. On GitHub Actions use the Supabase *Session pooler* URL (IPv4).
DATABASE_URL = os.getenv("DATABASE_URL")

# Lake storage, first match wins:
#   1. LAKE_S3_ENDPOINT set                         -> any S3-compatible store (S3 access keys)
#   2. SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY set -> Supabase Storage REST API
#   3. otherwise                                    -> local folder LAKE_LOCAL_DIR
LAKE_BUCKET = os.getenv("LAKE_BUCKET", "lake")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
LAKE_S3_ENDPOINT = os.getenv("LAKE_S3_ENDPOINT")
LAKE_S3_REGION = os.getenv("LAKE_S3_REGION", "us-east-1")
LAKE_S3_ACCESS_KEY_ID = os.getenv("LAKE_S3_ACCESS_KEY_ID")
LAKE_S3_SECRET_ACCESS_KEY = os.getenv("LAKE_S3_SECRET_ACCESS_KEY")
LAKE_LOCAL_DIR = Path(os.getenv("LAKE_LOCAL_DIR", ROOT / "data" / "lake"))

# Collector
MAX_COLLECT_SECONDS = _int("MAX_COLLECT_SECONDS", 480)
INITIAL_LOOKBACK_MINUTES = _int("INITIAL_LOOKBACK_MINUTES", 15)

# Retention (days)
BRONZE_RETENTION_DAYS = _int("BRONZE_RETENTION_DAYS", 3)
SILVER_RETENTION_DAYS = _int("SILVER_RETENTION_DAYS", 14)
PAGE_ACTIVITY_RETENTION_DAYS = _int("PAGE_ACTIVITY_RETENTION_DAYS", 3)
RUN_LOG_RETENTION_DAYS = _int("RUN_LOG_RETENTION_DAYS", 30)
ALERT_RETENTION_DAYS = _int("ALERT_RETENTION_DAYS", 90)

# Enrichment
ENRICH_BATCH_SIZE = _int("ENRICH_BATCH_SIZE", 60)
