"""Census Business Formation Statistics and FRED fetchers."""
from __future__ import annotations

import os
from datetime import datetime

from ..utils import http_get, write_output

BFS_API = "https://api.census.gov/data/timeseries/eits/bfs"
FRED_API = "https://api.stlouisfed.org/fred/series/observations"


def fetch_bfs(source: dict) -> dict:
    params = source.get("params", {})
    geo = params.get("geo", "CA")
    series = params.get("series", "BA_BA")
    year = datetime.now().year
    url = (f"{BFS_API}?get=cell_value,time_slot_id,seasonally_adj"
           f"&category_code={series}&data_type_code=TOTAL"
           f"&for=state:{_state_fips(geo)}"
           f"&time=from+2015+to+{year}")
    rows = http_get(url).json()
    header, body = rows[0], rows[1:]
    idx = {h: i for i, h in enumerate(header)}
    points = []
    for r in body:
        if r[idx.get("seasonally_adj", 2)] != "yes":
            continue
        t = r[idx["time"]]
        if "-" in t:  # monthly like 2024-03
            points.append({"date": t, "value": float(r[idx["cell_value"]])})
    points.sort(key=lambda p: p["date"])
    write_output(source["output"], {
        "status": "live",
        "source": "U.S. Census Bureau, Business Formation Statistics",
        "series": [{"id": f"BFS_{series}_{geo}",
                    "label": f"Business applications — {geo} (seasonally adj.)",
                    "points": points}],
    })
    return {"records": len(points), "note": f"{len(points)} monthly points"}


def fetch_fred(source: dict) -> dict:
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY secret not set (free at fred.stlouisfed.org)")
    params = source.get("params", {})
    out_series = []
    for s in params.get("series", []):
        url = (f"{FRED_API}?series_id={s['id']}&api_key={key}"
               f"&file_type=json&observation_start=2015-01-01")
        obs = http_get(url).json().get("observations", [])
        points = [{"date": o["date"][:7], "value": float(o["value"])}
                  for o in obs if o.get("value") not in (".", None)]
        out_series.append({"id": s["id"], "label": s.get("label", s["id"]),
                           "points": points})
    write_output(source["output"], {
        "status": "live",
        "source": "Federal Reserve Bank of St. Louis (FRED)",
        "series": out_series,
    })
    n = sum(len(s["points"]) for s in out_series)
    return {"records": n, "note": f"{len(out_series)} series, {n} points"}


def _state_fips(code: str) -> str:
    return {"CA": "06"}.get(code.upper(), code)
