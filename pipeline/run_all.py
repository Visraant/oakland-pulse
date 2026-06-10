"""Oakland Pulse pipeline orchestrator.

Usage:
    python -m pipeline.run_all              # run every enabled source
    python -m pipeline.run_all --only ID    # run one source by id
    python -m pipeline.run_all --list       # show configured sources

Each source runs independently: one failure never blocks the others.
Results land in data/<output>; per-source health lands in data/meta.json,
which both the dashboard footer and admin.html read.
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

import yaml

from .fetchers import REGISTRY
from .utils import DATA_DIR, now_iso

CONFIG = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"
META = DATA_DIR / "meta.json"


def load_sources() -> list[dict]:
    return yaml.safe_load(CONFIG.read_text())["sources"]


def load_meta() -> dict:
    if META.exists():
        try:
            return json.loads(META.read_text())
        except json.JSONDecodeError:
            pass
    return {"sources": {}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="run a single source id")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    sources = load_sources()
    if args.list:
        for s in sources:
            flag = "on " if s.get("enabled") else "off"
            print(f"[{flag}] {s['id']:32s} {s['type']:20s} -> {s['output']}")
        return 0

    meta = load_meta()
    failures = 0

    for source in sources:
        sid = source["id"]
        if args.only and sid != args.only:
            continue
        entry = meta["sources"].setdefault(sid, {})
        entry.update({"name": source["name"], "type": source["type"],
                      "category": source["category"],
                      "schedule": source.get("schedule"),
                      "output": source["output"],
                      "enabled": bool(source.get("enabled"))})
        if not source.get("enabled"):
            entry["status"] = "disabled"
            continue

        fetcher = REGISTRY.get(source["type"])
        if not fetcher:
            entry.update({"status": "error",
                          "error": f"unknown fetcher type '{source['type']}'"})
            failures += 1
            continue

        print(f"→ {sid} ({source['type']}) ...", flush=True)
        entry["last_run"] = now_iso()
        try:
            result = fetcher(source)
            entry.update({"status": "ok", "last_success": now_iso(),
                          "records": result.get("records"),
                          "note": result.get("note"), "error": None})
            print(f"  ✓ {result.get('note')}")
        except Exception as err:  # noqa: BLE001
            entry.update({"status": "error", "error": str(err)[:500]})
            failures += 1
            print(f"  ✗ {err}", file=sys.stderr)
            traceback.print_exc()

    meta["last_pipeline_run"] = now_iso()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps(meta, indent=1))
    print(f"\nDone. {failures} source(s) failed. Health written to data/meta.json")
    return 0  # always exit 0 so the workflow still commits partial updates


if __name__ == "__main__":
    raise SystemExit(main())
