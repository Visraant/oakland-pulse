"""Census Business Formation Statistics and FRED fetchers."""
from __future__ import annotations

import os
from datetime import datetime

from ..utils import http_get, write_output

BFS_API = "https://api.census.gov/data/timeseries/eits/bfs"
FRED_API = "https://api.stlouisfed.org/fred/series/observations"


def fetch_bfs(source: dict) -> dict:
    """US-level business applications. The Census BFS API publishes national
    data only (verified against /eits/bfs/geography); state-level BFS is a
    separate CSV product and can be added later as its own fetcher."""
    params = source.get("params", {})
    series = params.get("series", "BA_BA")
    points = []
    for year in range(2015, datetime.now().year + 1):
        url = (f"{BFS_API}?get=data_type_code,seasonally_adj,category_code,cell_value"
               f"&for=us:*&time={year}")
        try:
            rows = http_get(url).json()
        except Exception:  # noqa: BLE001
            continue  # a missing year shouldn't sink the series
        header, body = rows[0], rows[1:]
        idx = {h: i for i, h in enumerate(header)}
        for r in body:
            if (r[idx["data_type_code"]] == series
                    and r[idx["category_code"]] == "TOTAL"
                    and r[idx["seasonally_adj"]] == "yes"):
                points.append({"date": r[idx["time"]],
                               "value": float(r[idx["cell_value"]])})
    points.sort(key=lambda p: p["date"])
    if not points:
        raise RuntimeError("BFS API returned no matching rows")
    write_output(source["output"], {
        "status": "live",
        "source": "U.S. Census Bureau, Business Formation Statistics",
        "series": [{"id": f"BFS_{series}_US",
                    "label": "Business applications — US (seasonally adj.)",
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

