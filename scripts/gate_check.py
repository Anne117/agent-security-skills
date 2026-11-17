#!/usr/bin/env python3
"""Check a filled deployment-gate JSON and print a go/no-go verdict.

Usage:
    python3 gate_check.py gate.json
    python3 gate_check.py gate.json --today 2026-11-16

Exit codes: 0 = GO, 1 = NO-GO, 2 = usage or format error.
Stdlib only, no dependencies.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

REQUIRED = {
    "ID-1": "P0", "ID-2": "P0", "ID-3": "P1", "ID-4": "P1",
    "CAP-1": "P0", "CAP-2": "P0", "CAP-3": "P0", "CAP-4": "P1", "CAP-5": "P1",
    "DATA-1": "P0", "DATA-2": "P0", "DATA-3": "P1", "DATA-4": "P1",
    "INJ-1": "P0", "INJ-2": "P0", "INJ-3": "P1", "INJ-4": "P1",
    "OBS-1": "P0", "OBS-2": "P0", "OBS-3": "P1", "OBS-4": "P1",
    "SC-1": "P0", "SC-2": "P0", "SC-3": "P1", "SC-4": "P1",
}
VALID_STATUS = {"pass", "fail", "n/a", "pending"}


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("gate")
    ap.add_argument("--today", default=date.today().isoformat())
    args = ap.parse_args()

    try:
        doc = load(args.gate)
    except (OSError, json.JSONDecodeError) as e:
        print(f"cannot read gate file: {e}", file=sys.stderr)
        return 2

    checks = doc.get("checks") or {}
    waivers = {w.get("id"): w for w in (doc.get("waivers") or [])}
    today = date.fromisoformat(args.today)

    failures, waived, missing = [], [], []
    for cid, pri in REQUIRED.items():
        c = checks.get(cid)
        if not c:
            missing.append(cid)
            continue
        status = str(c.get("status", "")).lower()
        if status not in VALID_STATUS:
            failures.append((cid, pri, f"invalid status '{status}'"))
            continue
        if status == "pass":
            if not str(c.get("evidence", "")).strip():
                failures.append((cid, pri, "pass without evidence"))
            continue
        if status == "pending":
            failures.append((cid, pri, "not filled in"))
            continue
        if status == "n/a":
            if pri == "P0":
                failures.append((cid, pri, "P0 cannot be n/a"))
            continue
        # fail
        w = waivers.get(cid)
        if pri == "P0":
            failures.append((cid, pri, "P0 failure"))
        elif not w:
            failures.append((cid, pri, "P1 failure without waiver"))
        else:
            try:
                exp = date.fromisoformat(str(w.get("expires", "")))
            except ValueError:
                failures.append((cid, pri, "waiver without valid expiry"))
                continue
            if exp < today:
                failures.append((cid, pri, f"waiver expired {exp}"))
            elif not w.get("owner") or not w.get("compensating_control"):
                failures.append((cid, pri, "waiver missing owner or compensating control"))
            else:
                waived.append((cid, exp, w.get("owner")))

    p0 = sum(1 for f in failures if f[1] == "P0")
    p1 = len(failures) - p0

    print(f"agent: {doc.get('agent', '?')}  env: {doc.get('environment', '?')}")
    print(f"checks: {len(checks)}  required: {len(REQUIRED)}  "
          f"waived: {len(waived)}  failures: {len(failures)}  missing: {len(missing)}")
    for cid in missing:
        print(f"  MISSING  {cid} ({REQUIRED[cid]})")
    for cid, pri, why in failures:
        print(f"  FAIL     {cid} ({pri}) — {why}")
    for cid, exp, owner in waived:
        print(f"  WAIVED   {cid} until {exp} — {owner}")

    if p0 == 0 and p1 == 0 and not missing:
        print("VERDICT: GO")
        return 0
    print("VERDICT: NO-GO")
    return 1


if __name__ == "__main__":
    sys.exit(main())
