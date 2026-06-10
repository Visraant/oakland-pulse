"""Generic Socrata fetcher — works for data.oaklandca.gov, data.acgov.org,
or any other Socrata portal. Add a source block in sources.yaml with the
portal domain + dataset ID and this handles the rest.
"""
from __future__ import annotations

from collections import Counter

from ..utils import http_get, write_output


def fetch(source: dict) -> dict:
    params = source.get("params", {})
    domain, dataset = params["domain"], params["dataset_id"]
    if "REPLACE" in dataset.upper():
        raise RuntimeError("dataset_id not configured — set it in sources.yaml")
    soql = params.get("soql", "$limit=10000")
    url = f"https://{domain}/resource/{dataset}.json?{soql}"
    rows = http_get(url).json()

    payload: dict = {
        "status": "live",
        "source": f"https://{domain}/d/{dataset}",
        "row_count": len(rows),
        "rows": rows[:5000],
    }

    # If a date field is configured, also produce a monthly count series —
    # immediately chartable without custom code.
    date_field = params.get("date_field")
    if date_field and rows:
        counts = Counter(str(r.get(date_field, ""))[:7]
                         for r in rows if r.get(date_field))
        counts.pop("", None)
        payload["series"] = [{
            "id": f"{dataset}_{date_field}_monthly",
            "label": f"{source['name']} — monthly count",
            "points": [{"date": k, "value": v} for k, v in sorted(counts.items())],
        }]

    write_output(source["output"], payload)
    return {"records": len(rows), "note": f"{len(rows)} rows"}
