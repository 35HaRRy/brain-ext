import httpx
import pytest

from brainext.config import Config
from brainext.notion import _sync
from brainext.notion.client import NotionClient, NotionError


def test_incomplete_query_is_partitioned_without_losing_or_duplicating_rows(tmp_path, monkeypatch):
    monkeypatch.setattr("brainext.notion.client.time.sleep", lambda _: None)
    calls = []

    def handler(request):
        import json

        body = json.loads(request.content)
        calls.append(body)
        if "filter" not in body:
            return httpx.Response(200, json={"results": [{"id": "ignored"}], "has_more": False,
                                            "request_status": {"type": "incomplete"}})
        condition = body["filter"]["and"][0]["created_time"]
        value = "a" if "on_or_after" in condition and condition["on_or_after"].startswith("1970") else "b"
        return httpx.Response(200, json={"results": [{"id": value}], "has_more": False})

    with NotionClient(Config(tmp_path), "fake", httpx.MockTransport(handler)) as client:
        rows = list(_sync.data_source_rows(client, "00000000-0000-0000-0000-000000000001"))
    assert [row["id"] for row in rows] == ["a", "b"]
    assert len(calls) == 3


def test_blocked_reason_in_additional_data_does_not_retry(tmp_path, monkeypatch):
    monkeypatch.setattr("brainext.notion.client.time.sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, json={"code": "rate_limited", "additional_data": {
            "rate_limit_reason": "public_api_request_blocked"}})

    with NotionClient(Config(tmp_path), "fake", httpx.MockTransport(handler)) as client, pytest.raises(NotionError):
        client.request("GET", "/pages/00000000-0000-0000-0000-000000000001")
    assert len(calls) == 1
