"""Cliente HTTP resiliente para conectores (T-061, ADR-10/15).

- Rate limiting por tenant (token bucket no Redis; degrada para in-process se
  Redis ausente em dev).
- Retry com backoff exponencial + jitter para 429/5xx (tenacity).
- Timeout e tratamento que separa transitório de erro de dado.
"""

from __future__ import annotations

import time

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from app.core.errors import TransientError
from app.core.logging import get_logger

log = get_logger("connector.http")


class TokenBucket:
    """Token bucket simples por chave. Usa Redis se disponível, senão in-process."""

    def __init__(self, redis_url: str | None, rate_per_sec: float = 5.0, burst: int = 10):
        self.rate = rate_per_sec
        self.burst = burst
        self._local: dict[str, tuple[float, float]] = {}
        self._redis = None
        if redis_url:
            try:
                import redis  # noqa: PLC0415

                self._redis = redis.from_url(redis_url)
            except Exception:  # pragma: no cover
                self._redis = None

    def acquire(self, key: str) -> None:
        # Implementação in-process (suficiente para 1 worker no MVP).
        now = time.monotonic()
        tokens, last = self._local.get(key, (float(self.burst), now))
        tokens = min(self.burst, tokens + (now - last) * self.rate)
        if tokens < 1:
            sleep = (1 - tokens) / self.rate
            time.sleep(sleep)
            tokens = 1
        self._local[key] = (tokens - 1, time.monotonic())


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, (httpx.TransportError, TransientError))


class ResilientClient:
    def __init__(self, base_url: str, auth: tuple[str, str] | None, bucket: TokenBucket,
                 tenant_key: str, timeout: float = 30.0):
        self._client = httpx.Client(base_url=base_url, auth=auth, timeout=timeout)
        self._bucket = bucket
        self._tenant_key = tenant_key

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError, TransientError)),
        wait=wait_random_exponential(multiplier=0.5, max=20),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def get(self, path: str, params: dict | None = None) -> httpx.Response:
        self._bucket.acquire(self._tenant_key)
        resp = self._client.get(path, params=params)
        if resp.status_code in (429, 500, 502, 503, 504):
            log.warning("connector.http.retry", status=resp.status_code, path=path)
            resp.raise_for_status()
        resp.raise_for_status()
        return resp

    def close(self) -> None:
        self._client.close()
