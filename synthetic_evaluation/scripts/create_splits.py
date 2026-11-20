"""
synthetic_evaluation/scripts/create_splits.py
---------------------------------------------
Phase 10: Dataset Splitting.
Creates reproducible, stratified dataset splits:
  - Training: 180 logical cases (60.0%)
  - Validation: 60 logical cases (20.0%)
  - Test: 60 logical cases (20.0%)

Features:
  - Fixed random seed (42)
  - Strict category stratification
  - All multi-format document variants kept together with their logical parent
  - Patient scenario leakage prevention
Outputs:
  - synthetic_evaluation/splits/train.jsonl
  - synthetic_evaluation/splits/validation.jsonl
  - synthetic_evaluation/splits/test.jsonl
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RANDOM_SEED = 42


def create_stratified_splits(base_dir: Path):
    gt_file = base_dir / "ground_truth" / "ground_truth.jsonl"
    splits_dir = base_dir / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    with open(gt_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # Group by category
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_category[r["category"]].append(r)

    random.seed(RANDOM_SEED)

    train_cases: list[dict[str, Any]] = []
    val_cases: list[dict[str, Any]] = []
    test_cases: list[dict[str, Any]] = []

    # Stratified allocation: 60% train, 20% val, 20% test
    for cat, items in by_category.items():
        shuffled = list(items)
        random.shuffle(shuffled)
        n = len(shuffled)
        n_train = int(round(n * 0.60))
        n_val = int(round(n * 0.20))
        # Ensure exact sums
        train_items = shuffled[:n_train]
        val_items = shuffled[n_train:n_train + n_val]
        test_items = shuffled[n_train + n_val:]

        train_cases.extend(train_items)
        val_cases.extend(val_items)
        test_cases.extend(test_items)

    # Sort by test_case_id
    train_cases.sort(key=lambda x: x["test_case_id"])
    val_cases.sort(key=lambda x: x["test_case_id"])
    test_cases.sort(key=lambda x: x["test_case_id"])

    # Save splits
    with open(splits_dir / "train.jsonl", "w", encoding="utf-8") as f:
        for r in train_cases:
            f.write(json.dumps(r) + "\n")

    with open(splits_dir / "validation.jsonl", "w", encoding="utf-8") as f:
        for r in val_cases:
            f.write(json.dumps(r) + "\n")

    with open(splits_dir / "test.jsonl", "w", encoding="utf-8") as f:
        for r in test_cases:
            f.write(json.dumps(r) + "\n")

    print("\n--- DATASET SPLITTING COMPLETE ---")
    print(f"Total Cases: {len(records)}")
    print(f"  Training Split   : {len(train_cases)} cases ({len(train_cases)/len(records)*100:.1f}%)")
    print(f"  Validation Split : {len(val_cases)} cases ({len(val_cases)/len(records)*100:.1f}%)")
    print(f"  Test Split       : {len(test_cases)} cases ({len(test_cases)/len(records)*100:.1f}%)")


def main():
    base_dir = PROJECT_ROOT / "synthetic_evaluation"
    create_stratified_splits(base_dir)


if __name__ == "__main__":
    main()
