"""BLS public time-series API fetcher (LAUS unemployment, CES jobs).

Free without a key (limited daily requests); register a free key at
https://data.bls.gov/registrationEngine/ and add it as the BLS_API_KEY
repository secret for higher limits.
"""
from __future__ import annotations

import os
from datetime import datetime

from ..utils import http_post_json, write_output

API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


def fetch(source: dict) -> dict:
    params = source.get("params", {})
    series_cfg = params.get("series", [])
    labels = {s["id"]: s.get("label", s["id"]) for s in series_cfg}
    payload = {
        "seriesid": list(labels.keys()),
        "startyear": str(params.get("start_year", 2015)),
        "endyear": str(datetime.now().year),
    }
    key = os.environ.get("BLS_API_KEY")
    if key:
        payload["registrationkey"] = key

    data = http_post_json(API, payload)
    if data.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS API: {data.get('message') or data.get('status')}")

    out_series, rejected = [], []
    for s in data.get("Results", {}).get("series", []):
        sid = s.get("seriesID")
        points = []
        for item in s.get("data", []):
            period = item.get("period", "")
            if not period.startswith("M") or period == "M13":
                continue
            points.append({"date": f"{item['year']}-{period[1:]}",
                           "value": float(item["value"])})
        points.sort(key=lambda p: p["date"])
        if points:
            out_series.append({"id": sid, "label": labels.get(sid, sid),
                               "points": points})
        else:
            rejected.append(sid)

    for msg in data.get("message", []):
        rejected.append(str(msg))

    write_output(source["output"], {
        "status": "live",
        "source": "U.S. Bureau of Labor Statistics (api.bls.gov)",
        "series": out_series,
        "warnings": rejected,
    })
    n = sum(len(s["points"]) for s in out_series)
    note = f"{len(out_series)} series, {n} points"
    if rejected:
        note += f"; warnings: {rejected[:2]}"
    return {"records": n, "note": note}
