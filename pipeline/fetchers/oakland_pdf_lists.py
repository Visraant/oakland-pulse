"""Scraper for Oakland's monthly Opened/Closed Business Accounts PDFs.

The City posts two PDFs per month on a single page. This fetcher:
1. Loads the page and discovers every PDF link plus its month label.
2. Downloads any PDFs not yet cached.
3. Parses each PDF (tables first, text-line fallback) into records.
4. Writes monthly counts + record-level rows (name, address, NAICS/desc)
   so the dashboard can chart trends and map locations.
"""
from __future__ import annotations

import re

from ..utils import (download_pdf, http_get, month_key_from_label, pdf_tables,
                     pdf_text, write_output)

LINK_RE = re.compile(
    r'href="(?P<url>[^"]+open-closed-accounts/(?P<file>[^"]+\.pdf))"',
    re.IGNORECASE)

ZIP_RE = re.compile(r"\b(94[56]\d{2})\b")


def _classify(filename: str) -> str | None:
    name = filename.lower()
    if "opened" in name:
        return "opened"
    if "closed" in name:
        return "closed"
    return None


def _parse_pdf(path) -> list[dict]:
    """Best-effort extraction of business records from one monthly PDF."""
    records: list[dict] = []

    # Pass 1: structured tables
    for table in pdf_tables(path):
        for row in table:
            cells = [(c or "").strip() for c in row]
            cells = [c for c in cells if c]
            if len(cells) < 2:
                continue
            joined = " | ".join(cells)
            if re.search(r"business\s*name|account|page \d", joined, re.I):
                continue  # header rows
            rec = {"name": cells[0], "raw": joined}
            zips = ZIP_RE.findall(joined)
            if zips:
                rec["zip"] = zips[0]
            # heuristics: a cell containing a street number is the address
            for c in cells[1:]:
                if re.match(r"\d{2,6}\s+\w", c):
                    rec["address"] = c
                    break
            records.append(rec)

    # Pass 2: text lines, if tables yielded little
    if len(records) < 5:
        for line in pdf_text(path).splitlines():
            line = line.strip()
            if len(line) < 8 or re.search(r"city of oakland|page \d|report", line, re.I):
                continue
            if re.search(r"\d{2,6}\s+\w+.*(94[56]\d{2})", line):
                rec = {"name": line.split("  ")[0][:120], "raw": line}
                zips = ZIP_RE.findall(line)
                if zips:
                    rec["zip"] = zips[0]
                records.append(rec)

    return records


def fetch(source: dict) -> dict:
    page = http_get(source["url"]).text
    months_back = int(source.get("params", {}).get("months_back", 36))

    found: dict[tuple[str, str], str] = {}
    for match in LINK_RE.finditer(page):
        url, fname = match.group("url"), match.group("file")
        if url.startswith("/"):
            url = "https://www.oaklandca.gov" + url
        kind = _classify(fname)
        mkey = month_key_from_label(fname.replace("-", " "))
        if kind and mkey:
            found[(mkey, kind)] = url

    months = sorted({k[0] for k in found}, reverse=True)[:months_back]

    monthly: dict[str, dict] = {}
    sample_records: dict[str, dict[str, list]] = {}
    failures: list[str] = []

    for mkey in months:
        monthly[mkey] = {"opened": None, "closed": None}
        sample_records[mkey] = {"opened": [], "closed": []}
        for kind in ("opened", "closed"):
            url = found.get((mkey, kind))
            if not url:
                continue
            try:
                path = download_pdf(url, f"{kind}-{mkey}.pdf")
                recs = _parse_pdf(path)
                monthly[mkey][kind] = len(recs)
                sample_records[mkey][kind] = recs[:400]
            except Exception as err:  # noqa: BLE001
                failures.append(f"{mkey} {kind}: {err}")

    # ZIP-level counts for the map (most recent 12 months, openings net closings)
    zip_counts: dict[str, dict[str, int]] = {}
    for mkey in months[:12]:
        for kind in ("opened", "closed"):
            for rec in sample_records.get(mkey, {}).get(kind, []):
                z = rec.get("zip")
                if z:
                    zip_counts.setdefault(z, {"opened": 0, "closed": 0})
                    zip_counts[z][kind] += 1

    series = [{"month": m,
               "opened": monthly[m]["opened"],
               "closed": monthly[m]["closed"],
               "net": (monthly[m]["opened"] - monthly[m]["closed"])
               if monthly[m]["opened"] is not None and monthly[m]["closed"] is not None
               else None}
              for m in sorted(monthly)]

    write_output(source["output"], {
        "status": "live",
        "source": source["url"],
        "monthly": series,
        "zip_counts_12mo": zip_counts,
        "records_by_month": sample_records,
        "failures": failures,
    })
    parsed = sum(1 for s in series if s["opened"] is not None)
    return {"records": parsed, "note": f"{parsed} months parsed, {len(failures)} failures"}
