"""Census Business Formation Statistics and FRED fetchers."""
from __future__ import annotations

import os
from datetime import datetime

from ..utils import http_get, write_output

BFS_API = "https://api.census.gov/data/timeseries/eits/bfs"
FRED_API = "https://api.stlouisfed.org/fred/series/observations"


def fetch_bfs(source: dict) -> dict:
    """US-level business applications (the BFS API publishes national data
    only). One request for the whole range; GitHub runner IPs share Census's
    no-key quota, so add a free CENSUS_API_KEY secret if this rate-limits."""
    params = source.get("params", {})
    series = params.get("series", "BA_BA")
    url = (f"{BFS_API}?get=data_type_code,seasonally_adj,category_code,cell_value"
           f"&for=us:*&time=from+2015+to+{datetime.now().year}")
    key = os.environ.get("CENSUS_API_KEY")
    if key:
        url += f"&key={key}"
    rows = http_get(url).json()
    header, body = rows[0], rows[1:]
    idx = {h: i for i, h in enumerate(header)}

    def pick(adj):
        pts = [{"date": r[idx["time"]], "value": float(r[idx["cell_value"]])}
               for r in body
               if r[idx["data_type_code"]] == series
               and r[idx["category_code"]] == "TOTAL"
               and r[idx["seasonally_adj"]] == adj]
        pts.sort(key=lambda p: p["date"])
        return pts

    points, adj_note = pick("yes"), "seasonally adj."
    if not points:
        points, adj_note = pick("no"), "not seasonally adj."
    if not points:
        raise RuntimeError("BFS API returned no TOTAL rows for " + series)
    write_output(source["output"], {
        "status": "live",
        "source": "U.S. Census Bureau, Business Formation Statistics",
        "series": [{"id": f"BFS_{series}_US",
                    "label": f"Business applications — US ({adj_note})",
                    "points": points}],
    })
    return {"records": len(points), "note": f"{len(points)} monthly points ({adj_note})"}


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

