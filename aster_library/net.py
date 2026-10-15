"""Polite HTTP client: per-host rate limits, retries with backoff, on-disk cache.

Only public provider endpoints are contacted. No patient content, user data or
personal identifiers are ever sent; the identifying User-Agent names the
project, not a person.
"""
import hashlib
import json
import random
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

USER_AGENT = "AsterLibraryBuilder/1 (+https://github.com/AyushM1701/ASTER-AI)"

# Requests per second, chosen below each provider's published guidance.
HOST_RATES = {
    "eutils.ncbi.nlm.nih.gov": 2.5,  # NCBI: max 3/s without an API key
    "www.ebi.ac.uk": 5.0,
    "dailymed.nlm.nih.gov": 3.0,
    "medlineplus.gov": 1.0,
    "wsearch.nlm.nih.gov": 1.0,
    "api.github.com": 0.5,
    "codeload.github.com": 1.0,
    "clinicaltrials.gov": 2.0,
    "api.crossref.org": 2.0,
    "api.fda.gov": 2.0,
    "raw.githubusercontent.com": 5.0,
}
DEFAULT_RATE = 1.0


class FetchError(RuntimeError):
    pass


class PoliteClient:
    def __init__(self, cache_dir, *, timeout=60, max_retries=5, offline=False):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.offline = offline
        self._next = {}
        self._lock = threading.Lock()
        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=20),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            trust_env=True,
        )
        self.stats = {"requests": 0, "cache_hits": 0, "retries": 0, "failures": 0}

    def close(self):
        self.client.close()

    def _cache_path(self, url, params):
        key = url + "?" + json.dumps(params or {}, sort_keys=True)
        digest = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / digest[:2] / digest

    def _throttle(self, host):
        rate = HOST_RATES.get(host, DEFAULT_RATE)
        with self._lock:
            now = time.monotonic()
            wait = self._next.get(host, 0) - now
            self._next[host] = max(now, self._next.get(host, 0)) + 1 / rate
        if wait > 0:
            time.sleep(wait)

    def get(self, url, params=None, *, cache=True, max_bytes=60_000_000, accept=None):
        """Return (bytes, meta). Cached responses are content-identical replays."""
        path = self._cache_path(url, params)
        meta_path = path.with_suffix(".json")
        if cache and path.exists() and meta_path.exists():
            self.stats["cache_hits"] += 1
            return path.read_bytes(), json.loads(meta_path.read_text(encoding="utf-8"))
        if self.offline:
            raise FetchError(f"offline and not cached: {url}")
        host = urlsplit(url).hostname
        headers = {"Accept": accept} if accept else {}
        last = None
        for attempt in range(self.max_retries):
            self._throttle(host)
            try:
                self.stats["requests"] += 1
                with self.client.stream("GET", url, params=params, headers=headers) as response:
                    if response.status_code in (429, 500, 502, 503, 504):
                        retry_after = response.headers.get("Retry-After", "")
                        delay = float(retry_after) if retry_after.isdigit() else 2 ** attempt + random.random()
                        last = FetchError(f"HTTP {response.status_code} for {url}")
                        self.stats["retries"] += 1
                        time.sleep(min(delay, 60))
                        continue
                    if response.status_code == 404:
                        raise FetchError(f"HTTP 404 for {url}")
                    response.raise_for_status()
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > max_bytes:
                            raise FetchError(f"response exceeds {max_bytes} bytes: {url}")
                        chunks.append(chunk)
                    body = b"".join(chunks)
                    meta = {
                        "url": str(response.url),
                        "status": response.status_code,
                        "content_type": response.headers.get("content-type", ""),
                        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "sha256": hashlib.sha256(body).hexdigest(),
                        "bytes": len(body),
                    }
                if cache:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = path.with_suffix(".tmp")
                    tmp.write_bytes(body)
                    tmp.replace(path)
                    meta_path.write_text(json.dumps(meta), encoding="utf-8")
                return body, meta
            except FetchError:
                raise
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last = exc
                self.stats["retries"] += 1
                time.sleep(min(2 ** attempt + random.random(), 60))
        self.stats["failures"] += 1
        raise FetchError(f"failed after {self.max_retries} attempts: {url}: {last}")

    def get_json(self, url, params=None, **kwargs):
        body, _ = self.get(url, params, accept="application/json", **kwargs)
        return json.loads(body)
