"""One-time seed data generator.

Writes starter JSON files so the dashboard renders before the pipeline's
first run. Two kinds of content, never mixed:

  status "verified_seed" — real figures hand-verified on 2026-06-09 from the
                           cited public source.
  status "sample"        — synthetic placeholder series, generated with a
                           fixed seed, shown with a SAMPLE badge in the UI
                           until the pipeline overwrites the file.
"""
import json
import math
import random
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)
rng = random.Random(94612)

RETRIEVED = "2026-06-09"


def months(start_year, start_month, n):
    y, m = start_year, start_month
    out = []
    for _ in range(n):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def wave(n, base, amp, drift, noise):
    return [round(base + drift * i + amp * math.sin(i / 7) +
                  rng.uniform(-noise, noise), 1) for i in range(n)]


# ---------- Commercial real estate: REAL verified points ----------
cre_office = {
    "status": "verified_seed",
    "source": "CBRE Research — Oakland Figures",
    "note": f"Figures hand-verified from public CBRE/C&W pages on {RETRIEVED}; "
            "the pipeline extends this series automatically each quarter.",
    "points": [
        {"quarter": "2024-Q1", "segment": "office", "vacancy_pct": 21.2,
         "asking_rent_psf": 4.32, "net_absorption_sf": -235103,
         "source_url": "https://www.cbre.com/insights/figures/oakland-office-figures-q1-2024",
         "retrieved": RETRIEVED},
        {"quarter": "2026-Q1", "segment": "office", "vacancy_pct": 25.6,
         "asking_rent_psf": 3.69, "net_absorption_sf": -145792,
         "source_url": "https://www.cbre.com/insights/figures/oakland-office-figures-q1-2026",
         "retrieved": RETRIEVED},
    ],
}
json.dump(cre_office, open(DATA / "cre_office_cbre.json", "w"), indent=1)

cre_cushman = {
    "status": "verified_seed",
    "source": "Cushman & Wakefield — Oakland/East Bay MarketBeats",
    "points": [
        {"segment": "industrial", "vacancy_pct": 8.0, "retrieved": RETRIEVED,
         "period": "2026-Q1",
         "source_url": "https://www.cushmanwakefield.com/en/united-states/insights/us-marketbeats/oakland-marketbeats"},
        {"segment": "retail", "vacancy_pct": 7.2, "retrieved": RETRIEVED,
         "period": "2026-Q1",
         "source_url": "https://www.cushmanwakefield.com/en/united-states/insights/us-marketbeats/oakland-marketbeats"},
        {"segment": "office (Bay Area)", "vacancy_pct": 28.5, "retrieved": RETRIEVED,
         "period": "2026-Q1",
         "source_url": "https://www.cushmanwakefield.com/en/united-states/insights/us-marketbeats/oakland-marketbeats"},
    ],
}
json.dump(cre_cushman, open(DATA / "cre_cushman.json", "w"), indent=1)

# Extra verified CBRE points (industrial / R&D headline, Q1 2026)
cre_other = {
    "status": "verified_seed",
    "source": "CBRE Research — Oakland Figures",
    "points": [
        {"quarter": "2026-Q1", "segment": "industrial", "vacancy_pct": 7.6,
         "source_url": "https://www.cbre.com/offices/corporate/oakland",
         "retrieved": RETRIEVED},
        {"quarter": "2026-Q1", "segment": "R&D", "vacancy_pct": 19.3,
         "source_url": "https://www.cbre.com/offices/corporate/oakland",
         "retrieved": RETRIEVED},
    ],
}
json.dump(cre_other, open(DATA / "cre_other_cbre.json", "w"), indent=1)

# ---------- SAMPLE series (replaced by pipeline) ----------
n = 60
mlist = months(2021, 6, n)

emp = {
    "status": "sample",
    "source": "SAMPLE DATA — run the pipeline to replace with BLS figures",
    "series": [
        {"id": "sample_unemp_oakland", "label": "Oakland city — unemployment rate (%)",
         "points": [{"date": d, "value": max(3.2, v)} for d, v in
                    zip(mlist, wave(n, 6.8, 0.6, -0.025, 0.25))]},
        {"id": "sample_unemp_md", "label": "East Bay MD — unemployment rate (%)",
         "points": [{"date": d, "value": max(2.9, v - 1.1)} for d, v in
                    zip(mlist, wave(n, 6.4, 0.5, -0.022, 0.2))]},
    ],
}
json.dump(emp, open(DATA / "employment_unemployment.json", "w"), indent=1)

jobs = {
    "status": "sample",
    "source": "SAMPLE DATA — run the pipeline to replace with BLS figures",
    "series": [
        {"id": "sample_jobs_md", "label": "East Bay MD — total nonfarm jobs (thousands)",
         "points": [{"date": d, "value": round(v)} for d, v in
                    zip(mlist, wave(n, 1130, 12, 0.9, 4))]},
    ],
}
json.dump(jobs, open(DATA / "employment_jobs.json", "w"), indent=1)

bfs = {
    "status": "sample",
    "source": "SAMPLE DATA — run the pipeline to replace with Census BFS figures",
    "series": [
        {"id": "sample_bfs_ca", "label": "Business applications — CA (seasonally adj.)",
         "points": [{"date": d, "value": round(v * 100)} for d, v in
                    zip(mlist, wave(n, 430, 25, 0.4, 14))]},
    ],
}
json.dump(bfs, open(DATA / "business_formation.json", "w"), indent=1)

# Business accounts: sample monthly counts + ZIP distribution for the map
opened = [round(v) for v in wave(n, 310, 40, 0.3, 35)]
closed = [round(v) for v in wave(n, 230, 30, 0.1, 30)]
zips = ["94601", "94602", "94603", "94605", "94606", "94607", "94608",
        "94609", "94610", "94611", "94612", "94618", "94619", "94621"]
zip_counts = {}
for z in zips:
    o = rng.randint(40, 420) if z in ("94612", "94607", "94601", "94610") else rng.randint(15, 180)
    zip_counts[z] = {"opened": o, "closed": round(o * rng.uniform(0.5, 0.95))}

accounts = {
    "status": "sample",
    "source": "SAMPLE DATA — run the pipeline to parse the City's monthly PDFs",
    "monthly": [{"month": m, "opened": o, "closed": c, "net": o - c}
                for m, o, c in zip(mlist, opened, closed)],
    "zip_counts_12mo": zip_counts,
    "records_by_month": {},
}
json.dump(accounts, open(DATA / "business_accounts.json", "w"), indent=1)

# City finance: sample GPF revenue categories by fiscal quarter
quarters = [f"FY{y}-Q{q}" for y in (22, 23, 24, 25, 26) for q in (1, 2, 3, 4)][:18]
cats = {"property_tax": 95, "sales_tax": 18, "business_license_tax": 28,
        "real_estate_transfer_tax": 22, "transient_occupancy_tax": 7,
        "utility_consumption_tax": 13, "parking_tax": 5}
rev_reports = []
for i, qk in enumerate(quarters):
    figures = {k: round(v * 1e6 * (1 + 0.01 * i) * rng.uniform(0.85, 1.15))
               for k, v in cats.items()}
    figures["total_revenue"] = sum(figures.values())
    rev_reports.append({"label": f"R&E Report {qk}", "url": "#", "figures": figures,
                        "parsed_lines": len(figures)})
finance = {
    "status": "sample",
    "source": "SAMPLE DATA — run the pipeline to parse Finance Dept. PDFs",
    "report_kind": "revenue_expenditure",
    "reports": rev_reports,
    "failures": [],
}
json.dump(finance, open(DATA / "city_revenue.json", "w"), indent=1)

cash = {
    "status": "sample",
    "source": "SAMPLE DATA — run the pipeline to parse Finance Dept. PDFs",
    "report_kind": "cash_management",
    "reports": [{"label": f"Cash Mgmt {qk}", "url": "#",
                 "figures": {"total_portfolio": round(8.9e8 * (1 + 0.005 * i) * rng.uniform(0.96, 1.04))},
                 "parsed_lines": 1} for i, qk in enumerate(quarters)],
    "failures": [],
}
json.dump(cash, open(DATA / "city_cash.json", "w"), indent=1)

meta = {
    "last_pipeline_run": None,
    "sources": {
        "oakland_business_accounts": {"status": "seeded"},
        "bls_oakland_unemployment": {"status": "seeded"},
        "bls_oakland_jobs": {"status": "seeded"},
        "census_business_formation": {"status": "seeded"},
        "cbre_oakland_office": {"status": "seeded_verified"},
        "cushman_oakland_marketbeat": {"status": "seeded_verified"},
        "oakland_cash_management": {"status": "seeded"},
        "oakland_revenue_expenditure": {"status": "seeded"},
    },
}
json.dump(meta, open(DATA / "meta.json", "w"), indent=1)

print("Seed data written to", DATA)
