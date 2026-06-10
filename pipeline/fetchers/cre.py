"""Commercial real-estate fetchers: CBRE quarterly Figures pages and
Cushman & Wakefield MarketBeat pages.

These corporate pages have no API; the fetchers parse the headline summary
sentence, which has kept a stable format for years, e.g.:
  "...closed Q1 2026 with an overall vacancy rate of 25.6%, net absorption
   of negative 145,792 sq. ft., and an overall average asking rate of $3.69..."
If the publisher rephrases or blocks bots, the run is flagged on the admin
page and the dashboard keeps showing the last good data.
"""
from __future__ import annotations

import re
from datetime import datetime

from ..utils import http_get, read_output, write_output

VACANCY_RE = re.compile(r"overall vacancy rate of\s*([\d.]+)\s*%", re.I)
ABSORPTION_RE = re.compile(
    r"net absorption of\s*(negative\s*)?([\d,]+)\s*sq", re.I)
RENT_RE = re.compile(r"asking (?:rate|rent) of\s*\$([\d.]+)", re.I)


def _quarters(lookback: int):
    now = datetime.now()
    q = (now.month - 1) // 3 + 1
    year = now.year
    for _ in range(lookback):
        yield q, year
        q -= 1
        if q == 0:
            q, year = 4, year - 1


def fetch_cbre(source: dict) -> dict:
    params = source.get("params", {})
    template = params["url_template"]
    segment = params.get("segment", "office")
    lookback = int(params.get("lookback_quarters", 12))

    previous = read_output(source["output"]) or {}
    points = {p["quarter"]: p for p in previous.get("points", [])}
    fetched, failed = 0, []

    for q, year in _quarters(lookback):
        qkey = f"{year}-Q{q}"
        if qkey in points:
            continue  # already have it
        url = template.format(q=q, year=year)
        try:
            html = http_get(url).text
        except Exception as err:  # noqa: BLE001
            failed.append(f"{qkey}: {err}")
            continue
        vac = VACANCY_RE.search(html)
        if not vac:
            failed.append(f"{qkey}: page found but vacancy figure not located")
            continue
        point = {"quarter": qkey, "segment": segment,
                 "vacancy_pct": float(vac.group(1)),
                 "source_url": url, "retrieved": datetime.now().strftime("%Y-%m-%d")}
        ab = ABSORPTION_RE.search(html)
        if ab:
            val = float(ab.group(2).replace(",", ""))
            point["net_absorption_sf"] = -val if ab.group(1) else val
        rent = RENT_RE.search(html)
        if rent:
            point["asking_rent_psf"] = float(rent.group(1))
        points[qkey] = point
        fetched += 1

    ordered = [points[k] for k in sorted(points)]
    write_output(source["output"], {
        "status": "live" if ordered else "failed",
        "source": "CBRE Research — Oakland Figures",
        "points": ordered,
        "failures": failed,
    })
    return {"records": len(ordered),
            "note": f"{fetched} new quarters, {len(ordered)} total, {len(failed)} misses"}


def fetch_cushman(source: dict) -> dict:
    url = source["params"]["url"]
    html = http_get(url).text

    # The MarketBeat landing page summarizes each segment in prose.
    segments = {
        "office": r"(?:Bay Area|office)[^.]{0,200}?vacancy rate[^.]{0,80}?([\d.]+)\s*%",
        "industrial": r"industrial market[^.]{0,200}?vacancy rate of\s*([\d.]+)\s*%",
        "retail": r"retail market[^.]{0,250}?vacancy (?:rate\s*)?(?:at|of)\s*([\d.]+)\s*%",
    }
    today = datetime.now().strftime("%Y-%m-%d")
    previous = read_output(source["output"]) or {}
    points = previous.get("points", [])
    seen = {(p["segment"], p.get("retrieved")) for p in points}

    found = 0
    for seg, pattern in segments.items():
        m = re.search(pattern, html, re.I | re.S)
        if m and (seg, today) not in seen:
            points.append({"segment": seg, "vacancy_pct": float(m.group(1)),
                           "source_url": url, "retrieved": today})
            found += 1

    write_output(source["output"], {
        "status": "live" if found or points else "failed",
        "source": "Cushman & Wakefield — Oakland/East Bay MarketBeats",
        "points": points,
    })
    return {"records": len(points), "note": f"{found} segments parsed this run"}
