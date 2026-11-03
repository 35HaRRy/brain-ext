import importlib

import httpx
import pytest

from brainext.config import Config


def client_module():
    try:
        return importlib.import_module("brainext.notion.client")
    except ModuleNotFoundError:
        pytest.fail("Notion istemcisi henüz uygulanmadı")


@pytest.mark.parametrize("status", [429, 529, 503])
def test_read_retries_and_honors_retry_after(tmp_path, monkeypatch, status):
    module = client_module()
    waits = []
    monkeypatch.setattr(module.time, "sleep", waits.append)
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(status, headers={"Retry-After": "7"}, json={"code": "service_overload"})
        return httpx.Response(200, json={"id": "ok"})

    with module.NotionClient(Config(tmp_path), "secret", httpx.MockTransport(handler)) as client:
        assert client.request("GET", "/pages/x") == {"id": "ok"}
    assert len(calls) == 2
    assert calls[0].headers["Notion-Version"] == "2026-03-11"
    assert any(wait >= 7 for wait in waits)


@pytest.mark.parametrize("status,code", [(429, "public_api_request_blocked"), (403, "restricted_resource")])
def test_blocked_and_forbidden_never_retry_or_leak(tmp_path, monkeypatch, status, code, caplog):
    module = client_module()
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"code": code, "message": "secret-response"})

    with module.NotionClient(Config(tmp_path), "secret-token", httpx.MockTransport(handler)) as client:
        with pytest.raises(module.NotionError) as error:
            client.request("GET", "/pages/x")
    assert len(calls) == 1
    assert "secret" not in str(error.value) + repr(error.value) + caplog.text


@pytest.mark.parametrize("method", ["POST", "PATCH"])
def test_writes_503_are_uncertain_and_never_retried(tmp_path, monkeypatch, method):
    module = client_module()
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503, json={"message": "secret"})

    with module.NotionClient(Config(tmp_path), "secret", httpx.MockTransport(handler)) as client:
        with pytest.raises(module.UncertainWrite):
            client.request(method, "/pages", json={})
    assert len(calls) == 1


def test_throttle_is_shared_by_query_and_get_and_paths_cannot_exfiltrate(tmp_path, monkeypatch):
    module = client_module()
    now = [0.0]
    times = []

    def sleep(seconds):
        now[0] += seconds

    monkeypatch.setattr(module.time, "sleep", sleep)
    monkeypatch.setattr(module.time, "monotonic", lambda: now[0])

    def handler(request):
        times.append(now[0])
        return httpx.Response(200, json={})

    with module.NotionClient(Config(tmp_path), "secret", httpx.MockTransport(handler)) as client:
        client.request("GET", "/pages/x")
        client.request("POST", "/data_sources/x/query", json={})
        with pytest.raises(module.NotionError):
            client.request("GET", "https://attacker.invalid/")
    assert times == [0.0, 0.4]


@pytest.mark.parametrize("timeout", [False, True])
def test_non_json_write_response_and_transport_timeout_are_uncertain(tmp_path, monkeypatch, timeout):
    module = client_module()
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(request)
        if timeout:
            raise httpx.ReadTimeout("secret-token", request=request)
        return httpx.Response(200, text="secret")

    with module.NotionClient(Config(tmp_path), "secret-token", httpx.MockTransport(handler)) as client:
        with pytest.raises(module.UncertainWrite) as error:
            client.request("POST", "/pages", json={})
    assert len(calls) == 1
    assert "secret" not in str(error.value)
