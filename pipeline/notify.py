"""Tells the website that new gold data is published, so it re-renders without waiting for its cache."""

import logging

import requests

from pipeline import config

log = logging.getLogger(__name__)


def revalidate_site() -> bool:
    """Best-effort: a failed call only means the site refreshes on its normal schedule."""
    if not (config.SITE_REVALIDATE_URL and config.REVALIDATE_SECRET):
        return False
    try:
        resp = requests.post(
            config.SITE_REVALIDATE_URL,
            headers={"x-revalidate-secret": config.REVALIDATE_SECRET},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        log.warning("site revalidation failed: %s", exc)
        return False
