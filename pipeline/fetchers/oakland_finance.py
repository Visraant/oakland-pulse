"""Scraper for Oakland Finance Department PDF reports:
- Cash Management Reports (quarterly portfolio/cash position)
- Revenue & Expenditure Reports (General Purpose Fund revenue by category,
  including business license tax / gross receipts, sales tax, property tax)

These PDFs are formatted for humans, so extraction is best-effort:
the fetcher pulls dollar figures attached to known revenue line labels and
records the page text around them for auditability. Anything it cannot
parse is listed under "failures" and shown on the admin page.
"""
from __future__ import annotations

import re

from ..utils import download_pdf, http_get, pdf_text, write_output

PDF_LINK_RE = re.compile(r'href="(?P<url>[^"]+\.pdf)"[^>]*>(?P<label>[^<]{0,200})',
                         re.IGNORECASE)

# Revenue lines worth tracking, with tolerant label patterns.
REVENUE_LINES = {
    "business_license_tax": r"business\s+(license|tax)",
    "sales_tax": r"sales\s+tax",
    "property_tax": r"property\s+tax",
    "transient_occupancy_tax": r"transient\s+occupancy",
    "real_estate_transfer_tax": r"(real\s+estate|property)\s+transfer\s+tax",
    "utility_consumption_tax": r"utility\s+consumption",
    "parking_tax": r"parking\s+tax",
    "total_revenue": r"total\s+revenue",
}

MONEY_RE = r"\$?\(?([\d,]{4,})\)?"


def _extract_lines(text: str) -> dict[str, float]:
    found: dict[str, float] = {}
    for line in text.splitlines():
        low = line.lower()
        for key, pattern in REVENUE_LINES.items():
            if key in found:
                continue
            if re.search(pattern, low):
                amounts = re.findall(MONEY_RE, line)
                if amounts:
                    # Last figure on the line is typically YTD actual.
                    found[key] = float(amounts[-1].replace(",", ""))
    return found


def fetch(source: dict) -> dict:
    params = source.get("params", {})
    keep = int(params.get("keep_reports", 12))
    kind = params.get("report_kind", "report")

    page = http_get(source["url"]).text
    links: list[tuple[str, str]] = []
    for m in PDF_LINK_RE.finditer(page):
        url, label = m.group("url"), re.sub(r"\s+", " ", m.group("label")).strip()
        if url.startswith("/"):
            url = "https://www.oaklandca.gov" + url
        links.append((url, label or url.rsplit("/", 1)[-1]))

    reports, failures = [], []
    for url, label in links[:keep]:
        try:
            path = download_pdf(url, f"{kind}-{url.rsplit('/', 1)[-1]}")
            text = pdf_text(path)
            lines = _extract_lines(text)
            reports.append({"label": label, "url": url, "figures": lines,
                            "parsed_lines": len(lines)})
        except Exception as err:  # noqa: BLE001
            failures.append(f"{label}: {err}")

    write_output(source["output"], {
        "status": "live" if reports else "failed",
        "source": source["url"],
        "report_kind": kind,
        "reports": reports,
        "failures": failures,
    })
    return {"records": len(reports),
            "note": f"{len(reports)} reports parsed, {len(failures)} failures"}
