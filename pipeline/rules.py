"""Business rules shared by the batch pipeline and the local Spark streaming mode.

Keep this module free of third-party imports so Spark containers can import it as-is.
"""

# wiki id -> display name. Only these wikis are kept; everything else is dropped at ingestion.
TRACKED_WIKIS = {
    "enwiki": "English",
    "hiwiki": "Hindi",
    "mrwiki": "Marathi",
    "bnwiki": "Bengali",
    "tawiki": "Tamil",
    "tewiki": "Telugu",
    "knwiki": "Kannada",
    "mlwiki": "Malayalam",
    "guwiki": "Gujarati",
    "pawiki": "Punjabi",
    "urwiki": "Urdu",
}
INDIAN_WIKIS = [w for w in TRACKED_WIKIS if w != "enwiki"]

ARTICLE_NAMESPACE = 0                      # main/article namespace only
TRACKED_CHANGE_TYPES = ("edit", "new")     # skip log + categorize events

# IPv4, IPv6 (usernames cannot contain ':') or temporary accounts (start with '~').
# RE2 / Java / Postgres compatible.
ANON_USER_REGEX = r"^(\d{1,3}\.){3}\d{1,3}$|:|^~"

BUCKET_MINUTES = 15

# Trending / breaking thresholds (mirrored in supabase/migrations/*_init.sql refresh_trending()).
TRENDING_MIN_HUMAN_EDITS = 2
BREAKING_MIN_SPIKE_SCORE = 5
BREAKING_MIN_HUMAN_EDITS = 8
BREAKING_MIN_EDITORS = 3


def keep_event(event: dict) -> bool:
    """True when a recentchange event belongs in the lake."""
    return (
        event.get("wiki") in TRACKED_WIKIS
        and event.get("namespace") == ARTICLE_NAMESPACE
        and event.get("type") in TRACKED_CHANGE_TYPES
    )


def wiki_language(wiki: str) -> str:
    """'enwiki' -> 'en'."""
    return wiki[:-4] if wiki.endswith("wiki") else wiki


def wiki_host(wiki: str) -> str:
    return f"{wiki_language(wiki)}.wikipedia.org"
