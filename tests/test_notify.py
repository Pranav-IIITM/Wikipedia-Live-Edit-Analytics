import requests

from pipeline import config, notify


class FakeResponse:
    def __init__(self, status):
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


def test_skipped_when_not_configured(monkeypatch):
    monkeypatch.setattr(config, "SITE_REVALIDATE_URL", None)
    assert notify.revalidate_site() is False


def test_posts_secret_header_and_tolerates_failure(monkeypatch):
    monkeypatch.setattr(config, "SITE_REVALIDATE_URL", "https://example.test/api/revalidate")
    monkeypatch.setattr(config, "REVALIDATE_SECRET", "s3cret")
    calls = []

    def fake_post(url, headers, timeout):
        calls.append((url, headers))
        return FakeResponse(status)

    monkeypatch.setattr(notify.requests, "post", fake_post)
    status = 200
    assert notify.revalidate_site() is True
    assert calls[0] == ("https://example.test/api/revalidate", {"x-revalidate-secret": "s3cret"})
    status = 401
    assert notify.revalidate_site() is False   # never raises: the run already succeeded
