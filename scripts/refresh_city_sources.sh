#!/usr/bin/env bash
# The City's website returns HTTP 403 to GitHub's datacenter IPs, so the
# three oaklandca.gov sources must run from a network the site trusts —
# any City workstation works. Run this manually or on a weekly cron;
# everything else stays on the GitHub cloud schedule.
set -e
cd "$(dirname "$0")/.."
PY="$(command -v python3 || command -v python)"
"$PY" -m pip install -q -r requirements.txt
"$PY" -m pipeline.run_all --only oakland_business_accounts
"$PY" -m pipeline.run_all --only oakland_cash_management
"$PY" -m pipeline.run_all --only oakland_revenue_expenditure
git pull --rebase origin main
git add data/
git diff --cached --quiet || git commit -m "data: city-source refresh from trusted network"
git push origin main
echo "Done — check https://visraant.github.io/oakland-pulse/admin.html in ~2 minutes."
