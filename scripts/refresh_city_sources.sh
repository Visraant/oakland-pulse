#!/usr/bin/env bash
# The City's website (Granicus/OpenCities) returns HTTP 403 to GitHub's
# datacenter IPs, so the three oaklandca.gov sources must run from a network
# the site trusts — any City workstation or laptop works. Run this weekly
# (or via cron/Task Scheduler); everything else stays on the GitHub schedule.
set -e
cd "$(dirname "$0")/.."
pip install -q -r requirements.txt
python -m pipeline.run_all --only oakland_business_accounts
python -m pipeline.run_all --only oakland_cash_management
python -m pipeline.run_all --only oakland_revenue_expenditure
git pull --rebase origin main
git add data/
git diff --cached --quiet || git commit -m "data: city-source refresh from trusted network"
git push origin main
