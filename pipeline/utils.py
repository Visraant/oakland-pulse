"""Shared helpers for Oakland Pulse fetchers."""
from __future__ import annotations

import io
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

try:  # browser-impersonating client; needed because oaklandca.gov's bot
    # protection fingerprints plain Python clients and returns HTTP 403
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_DIR = DATA_DIR / "_cache"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 OaklandPulse/1.0 "
      "(civic data dashboard; contact: see repo)")

MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}
MONTHS.update({"sept": 9, "june": 6, "july": 7, "march": 3, "april": 4,
               "january": 1, "february": 2, "august": 8, "september": 9,
               "october": 10, "november": 11, "december": 12})


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_get(url: str, *, timeout: int = 60, retries: int = 3,
             backoff: float = 2.0, **kwargs) -> requests.Response:
    """GET with a real user agent and simple exponential backoff."""
    headers = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    headers.update(kwargs.pop("headers", {}))
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            # Prefer a real-Chrome TLS/HTTP fingerprint (some government and
            # corporate sites 403 plain Python clients); fall back to plain
            # requests on the final attempt so curl_cffi issues can never
            # take down a source that worked before.
            if curl_requests is not None and attempt < retries - 1:
                resp = curl_requests.get(url, impersonate="chrome",
                                         timeout=timeout, **kwargs)
            else:
                resp = requests.get(url, headers=headers, timeout=timeout, **kwargs)
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code} from {url.split('/')[2]}"
                                   + (" (likely bot protection)" if resp.status_code in (403, 429, 503) else ""))
            return resp
        except Exception as err:  # noqa: BLE001
            last_err = err
            time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries} attempts: {url} — {last_err}")


def http_post_json(url: str, payload: dict, *, timeout: int = 60) -> dict:
    headers = {"User-Agent": UA, "Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def download_pdf(url: str, cache_name: str) -> Path:
    """Download a PDF once; reuse the cached copy on later runs."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", cache_name)
    path = CACHE_DIR / safe
    if path.exists() and path.stat().st_size > 0:
        return path
    resp = http_get(url)
    path.write_bytes(resp.content)
    return path


def pdf_text(path: Path) -> str:
    import pdfplumber
    out = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            out.append(page.extract_text() or "")
    return "\n".join(out)


def pdf_tables(path: Path) -> list[list[list[str]]]:
    import pdfplumber
    tables = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for tbl in page.extract_tables() or []:
                tables.append(tbl)
    return tables


def write_output(filename: str, payload: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload.setdefault("generated_at", now_iso())
    (DATA_DIR / filename).write_text(json.dumps(payload, indent=1))


def read_output(filename: str) -> dict | None:
    path = DATA_DIR / filename
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return None
    return None


def month_key_from_label(text: str) -> str | None:
    """'Opened Business Accounts Mar 2026' -> '2026-03'."""
    m = re.search(r"([A-Za-z]{3,9})\.?\s+(\d{4})", text)
    if not m:
        return None
    mon = MONTHS.get(m.group(1).lower()[:4]) or MONTHS.get(m.group(1).lower()[:3])
    if not mon:
        return None
    return f"{m.group(2)}-{mon:02d}"
