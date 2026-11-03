"""Tek kuyruklu HTTP istemcisi; uzak hata metinleri dışarı taşınmaz."""

from __future__ import annotations

import math
import random
import threading
import time
from uuid import UUID

import httpx

from brainext.config import Config


class NotionError(Exception):
    def __init__(self, status: int = 0, *, blocked: bool = False):
        self.status = status
        self.blocked = blocked
        super().__init__("Notion isteği engellendi" if blocked else "Notion isteği tamamlanamadı")


class UncertainWrite(NotionError):
    def __init__(self, status: int = 0, committed_resource_id: str | None = None):
        super().__init__(status)
        self.args = ("Notion yazma sonucu belirsiz; yeniden gönderilmedi",)
        self.committed_resource_id = None
        try:
            self.committed_resource_id = str(UUID(committed_resource_id))
        except (ValueError, TypeError, AttributeError):
            pass


class NotionClient:
    def __init__(self, config: Config, token: str, transport=None):
        self._http = httpx.Client(
            base_url="https://api.notion.com/v1/",
            headers={"Authorization": f"Bearer {token}", "Notion-Version": config.api_version},
            transport=transport, timeout=30, follow_redirects=False,
        )
        self._interval = 1 / config.requests_per_second
        self._next = 0.0
        self._queue = threading.Lock()

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def request(self, method: str, path: str, *, json=None, params=None) -> dict:
        method = method.upper()
        if not path.startswith("/") or path.startswith("//") or any(
            x in path for x in (":", "\\", "..", "?", "#")
        ):
            raise NotionError()
        read = method == "GET" or (
            method == "POST" and path.startswith("/data_sources/") and path.endswith("/query")
        )
        with self._queue:
            for attempt in range(5):
                time.sleep(max(0, self._next - time.monotonic()))
                self._next = time.monotonic() + self._interval
                response = None
                try:
                    response = self._http.request(method, path.lstrip("/"), json=json, params=params)
                except httpx.HTTPError:
                    pass
                if response is None:
                    if not read:
                        raise UncertainWrite() from None
                    if attempt == 4:
                        raise NotionError() from None
                    time.sleep(2**attempt + random.random())
                    continue
                try:
                    data = response.json()
                    valid = isinstance(data, dict)
                except (ValueError, UnicodeError):
                    data = {}
                    valid = False
                data = data if valid else {}
                status = response.status_code
                if 200 <= status < 300:
                    if valid:
                        return data
                    raise (NotionError(status) if read else UncertainWrite(status))
                extra = data.get("additional_data")
                extra = extra if isinstance(extra, dict) else {}
                if (data.get("code") == "public_api_request_blocked"
                        or extra.get("rate_limit_reason") == "public_api_request_blocked"):
                    raise NotionError(status, blocked=True)
                try:
                    delay = float(response.headers.get("Retry-After", "0"))
                    if not math.isfinite(delay) or delay < 0:
                        delay = 0
                except ValueError:
                    delay = 0
                retry = status == 429 or (read and status >= 500)
                if retry and attempt < 4:
                    time.sleep(max(delay, 2**attempt + random.random() if status >= 500 else 0))
                    continue
                if not read and status >= 500:
                    if status == 529:
                        time.sleep(delay)
                    extra = data.get("additional_data")
                    extra = extra if isinstance(extra, dict) else {}
                    raise UncertainWrite(status, extra.get("committed_resource_id"))
                raise NotionError(status)
        raise NotionError()
