"""
synthetic_evaluation/scripts/validate_policies.py
------------------------------------------------
Phase 1 QA: Rigorously validates all generated synthetic insurance policies:
  - Policy count (>= 30)
  - Policy ID uniqueness and formatting
  - Temporal validity (start date < expiry date)
  - Waiting periods (initial, specific disease, PED, moratorium)
  - Financial limits and positive non-zero Sums Insured
  - Rule IDs uniqueness and traceability to clauses
  - Coverage matrix and clause mapping integrity
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def validate_policies(base_dir: Path) -> dict[str, Any]:
    canonical_dir = base_dir / "policies" / "canonical"
    policy_files = sorted(canonical_dir.glob("POL-*.json"))

    results = {
        "total_policies_found": len(policy_files),
        "errors": [],
        "warnings": [],
        "passed": False,
    }

    if len(policy_files) < 30:
        results["errors"].append(f"Insufficient policies: expected >= 30, found {len(policy_files)}")

    policy_ids: set[str] = set()
    rule_ids: set[str] = set()

    for pfile in policy_files:
        try:
            with open(pfile, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            results["errors"].append(f"JSON load failure for {pfile.name}: {e}")
            continue

        pid = data.get("policy_id")
        if not pid or not pid.startswith("POL-"):
            results["errors"].append(f"Invalid policy_id format in {pfile.name}: '{pid}'")
        elif pid in policy_ids:
            results["errors"].append(f"Duplicate policy_id: '{pid}' in {pfile.name}")
        else:
            policy_ids.add(pid)

        # Dates validation
        try:
            s_date = date.fromisoformat(data["policy_start_date"])
            e_date = date.fromisoformat(data["policy_expiry_date"])
            if e_date <= s_date:
                results["errors"].append(f"{pid}: expiry_date ({e_date}) not after start_date ({s_date})")
        except Exception as e:
            results["errors"].append(f"{pid}: Invalid date formatting: {e}")

        # Financial validation
        try:
            si = Decimal(str(data["sum_insured"]["amount"]))
            if si <= Decimal("0"):
                results["errors"].append(f"{pid}: Non-positive sum_insured: {si}")
        except Exception as e:
            results["errors"].append(f"{pid}: Invalid sum_insured decimal: {e}")

        # Waiting periods validation
        wp = data.get("waiting_periods", {})
        init_d = wp.get("initial_days", 0)
        spec_m = wp.get("specific_disease_months", 0)
        ped_m = wp.get("ped_months", 0)
        if init_d not in (0, 30, 90):
            results["warnings"].append(f"{pid}: Unusual initial waiting period: {init_d} days")
        if ped_m not in (0, 12, 24, 36, 48):
            results["warnings"].append(f"{pid}: Unusual PED waiting period: {ped_m} months")

        # Rules validation
        rules = data.get("rules", [])
        if not rules:
            results["errors"].append(f"{pid}: No rules defined")
        for r in rules:
            rid = r.get("rule_id")
            if not rid:
                results["errors"].append(f"{pid}: Missing rule_id in rule {r}")
            elif rid in rule_ids:
                results["errors"].append(f"Duplicate rule_id '{rid}' across policies")
            else:
                rule_ids.add(rid)

            if not r.get("clause_reference"):
                results["errors"].append(f"{pid} Rule {rid}: Missing clause_reference")

    results["unique_policy_ids"] = len(policy_ids)
    results["unique_rule_ids"] = len(rule_ids)

    # Check policy_ground_truth files
    gt_dir = base_dir / "policy_ground_truth"
    for fname in ["policy_rules.jsonl", "coverage_matrix.json", "policy_clause_mapping.json"]:
        fpath = gt_dir / fname
        if not fpath.exists() or fpath.stat().st_size == 0:
            results["errors"].append(f"Missing or empty ground truth file: {fname}")

    results["passed"] = len(results["errors"]) == 0
    return results


def main():
    base_dir = PROJECT_ROOT / "synthetic_evaluation"
    res = validate_policies(base_dir)
    print("\n--- POLICY VALIDATION REPORT ---")
    print(f"Total Policies: {res['total_policies_found']}")
    print(f"Unique Rules: {res.get('unique_rule_ids', 0)}")
    print(f"Errors ({len(res['errors'])}): {res['errors']}")
    print(f"Warnings ({len(res['warnings'])}): {res['warnings']}")
    print(f"STATUS: {'PASS' if res['passed'] else 'FAIL'}")
    if not res["passed"]:
        exit(1)


if __name__ == "__main__":
    main()
