# Oakland Pulse — East Bay Economic Monitor

A self-updating dashboard of real-time and historical economic activity in
Oakland and the broader East Bay: commercial vacancy, business openings and
closings, City revenue (including gross receipts / business license tax),
employment, and business formation — interactive across time, geography, and
sector, with charts, tables, and a map.

**Architecture (deliberately boring and free):**

```
config/sources.yaml        ← the source registry (admin-editable, plain text)
pipeline/                  ← Python fetchers & scrapers, one per source type
data/*.json                ← the only thing the website reads
index.html                 ← the dashboard (Plotly + Leaflet, no build step)
admin.html                 ← source registry, health status, edit instructions
.github/workflows/         ← daily scheduled refresh via GitHub Actions
```

Static hosting + a scheduled job means no servers to maintain, no database,
no monthly bill, and version control on every data refresh (you can see
exactly what changed and when, and roll anything back).

## Deploy in ~10 minutes

1. **Create a GitHub repository** and upload this folder (or `git push` it).
2. **Enable GitHub Pages:** repo → Settings → Pages → Source: *Deploy from a
   branch* → `main` / root. Your dashboard is now live at
   `https://<org>.github.io/<repo>/`.
3. **Turn on the scheduler:** the workflow in
   `.github/workflows/update-data.yml` runs daily at ~6am Pacific and commits
   refreshed JSON. Run it once now: Actions → *Update data* → *Run workflow*.
4. **(Optional) Add API keys** as repo secrets (Settings → Secrets →
   Actions): `BLS_API_KEY` (free, raises BLS rate limits) and `FRED_API_KEY`
   (only if you enable FRED sources).
5. **Set the repo URL** in `admin.html` (the one-line `REPO` constant) so the
   admin page's edit/run buttons deep-link correctly.

To preview locally: `pip install -r requirements.txt`, then
`python -m http.server` in this folder and open http://localhost:8000.
(Opening index.html directly from disk won't load the JSON files —
browsers block `file://` fetches.)

## Running the pipeline

```bash
python -m pipeline.run_all            # refresh every enabled source
python -m pipeline.run_all --only oakland_business_accounts
python -m pipeline.run_all --list
```

Each source runs independently; a failure in one never blocks the others.
Per-source health (last run, last success, record counts, error messages)
is written to `data/meta.json` and displayed on **admin.html**.

## How an administrator edits sources (no coding)

Everything the dashboard ingests is declared in `config/sources.yaml`.
On GitHub, open the file → pencil icon → edit → *Commit changes*:

- **Pause a source:** `enabled: true` → `false`
- **Fix a moved page:** change the `url:` line
- **Add any Socrata dataset** (data.oaklandca.gov, data.acgov.org,
  data.ca.gov…): copy the template block at the bottom of the file and paste
  the dataset ID from the portal's "API" button. A `date_field` gives you an
  automatic monthly trend chart with zero code.

The admin page (`admin.html`) renders this registry alongside live health
status so non-technical staff can always see what feeds the dashboard,
where it comes from, and whether it's working.

## What's seeded vs. live

The repo ships with starter data so the dashboard renders immediately:

- **Verified seed** (blue badge): real published figures hand-checked on
  2026-06-09 — e.g. CBRE's Oakland office vacancy of 25.6% for Q1 2026 and
  Cushman & Wakefield's East Bay industrial (8.0%) and retail (7.2%) rates.
- **Sample** (amber badge): synthetic placeholder series, clearly labeled,
  that the first pipeline run overwrites with real BLS / Census / City data.

## First-run verification checklist

1. **BLS series IDs** — confirm the LAUS/CES IDs in `sources.yaml` at
   https://data.bls.gov/series-report (the BLS area-code scheme is fiddly;
   the pipeline flags any rejected series on the admin page).
2. **Oakland PDF parsing** — the City's opened/closed account PDFs and
   Finance reports are formatted for humans; the parsers are tolerant but
   check the first run's record counts against one PDF by eye. Unparsed
   items are listed under `failures` in the output JSON.
3. **CBRE / Cushman pages** — scraped politely (one page per quarter,
   cached, real user agent). Corporate sites occasionally block bots; if a
   quarter fails it's flagged, and figures can be appended by hand to
   `data/cre_office_cbre.json` in the same format.

## Extending

- **New fetcher types** (a new PDF layout, an API with auth, ESRI/ArcGIS
  feeds): add one function in `pipeline/fetchers/`, register it in
  `fetchers/__init__.py`, and it becomes available as a `type:` in the YAML.
- **Worth adding next:** Alameda County sales tax data (CDTFA), Port of
  Oakland TEU volumes, OAK airport passenger stats, BART ridership by
  station (real foot-traffic proxy), Census County Business Patterns for
  sector-level revenue/payroll, and the City's own open-data portal datasets
  as they're published.

## Known issue: oaklandca.gov blocks cloud IPs

The City's website platform returns HTTP 403 to requests from GitHub's
servers (bot protection by IP reputation). The three oaklandca.gov sources
therefore can't refresh from the cloud scheduler. Two clean fixes:

1. **Run them from a trusted network** — `scripts/refresh_city_sources.sh`
   refreshes just those sources and pushes the data; run it from any City
   machine on a weekly cron. (As City staff you could also ask IT/Granicus
   to allowlist a runner, or better, get Finance to publish these as data
   files on data.oaklandca.gov — then they become one-line Socrata sources.)
2. **A self-hosted GitHub Actions runner** inside the City network makes it
   fully automatic.

## Honest limitations

- Scrapers were written against page structures verified on 2026-06-09 but
  could not be executed end-to-end against the live sites from the build
  environment — expect to spend a short session on the first run tuning the
  PDF table heuristics and confirming series IDs (the admin page tells you
  exactly what failed and why).
- "Revenue generated by businesses, by sector" is not published at city
  level in real time anywhere; the dashboard proxies it with the City's
  business-license (gross receipts) tax line, Census business formation,
  and sector employment. County Business Patterns (annual) is the best
  sector-revenue addition if you want to go deeper.
- GitHub Pages is public. If the dashboard must be internal-only, the same
  repo deploys unchanged to Cloudflare Pages/Netlify behind access control,
  or to a City web server with a cron job instead of GitHub Actions.
