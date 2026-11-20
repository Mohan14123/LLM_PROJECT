"""
synthetic_evaluation/scripts/run_all.py
---------------------------------------
Master Automation Runner: Executes the entire 12-phase Synthetic Data Generation
and Evaluation pipeline end-to-end in strict dependency sequence.

Sequence:
  1. generate_policies.py       -> Generates 35 canonical policies & 101 rules
  2. validate_policies.py       -> Validates policy integrity and schemas
  3. render_policy_documents.py -> Renders 210 policy documents (JSON, TXT, PDF, DOCX, PNG, JPG)
  4. generate_patient_scenarios.py -> Generates 300 policy-linked patient scenarios
  5. generate_test_cases.py     -> Generates 300 logical cases (100, 80, 45, 30, 25, 20)
  6. render_request_documents.py-> Renders 1,800 request documents across 6 formats with OCR stress
  7. generate_ground_truth.py   -> Generates canonical ground truth and field mappings
  8. create_splits.py           -> Creates stratified Train (180), Val (60), Test (60) splits
  9. evaluate_results.py        -> Evaluates pipeline, extraction, schema, and rules
  10. validate_dataset.py       -> Final QA audit and manifest generation
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent.parent
PYTHON = sys.executable

STEPS = [
    ("Phase 1: Generate Synthetic Policies", SCRIPTS_DIR / "generate_policies.py"),
    ("Phase 1 QA: Validate Policies", SCRIPTS_DIR / "validate_policies.py"),
    ("Phase 2: Render Policy Documents (6 formats)", SCRIPTS_DIR / "render_policy_documents.py"),
    ("Phase 3: Generate Patient Scenarios", SCRIPTS_DIR / "generate_patient_scenarios.py"),
    ("Phase 4: Generate 300 Logical Test Cases", SCRIPTS_DIR / "generate_test_cases.py"),
    ("Phase 5: Render Request Documents (6 formats + OCR)", SCRIPTS_DIR / "render_request_documents.py"),
    ("Phase 6-7: Generate Canonical Ground Truth", SCRIPTS_DIR / "generate_ground_truth.py"),
    ("Phase 10: Create Stratified Splits (Train/Val/Test)", SCRIPTS_DIR / "create_splits.py"),
    ("Phase 8-9: Multi-Dimensional Evaluation Engine", SCRIPTS_DIR / "evaluate_results.py"),
    ("Phase 16 QA: Comprehensive Dataset Audit & Manifest", SCRIPTS_DIR / "validate_dataset.py"),
]


def run_pipeline():
    print("=" * 80)
    print("STARTING END-TO-END POLICY-FIRST SYNTHETIC BENCHMARK PIPELINE")
    print("=" * 80)
    start_total = time.perf_counter()

    for idx, (title, script_path) in enumerate(STEPS, start=1):
        print(f"\n[{idx}/{len(STEPS)}] Running {title}...")
        step_start = time.perf_counter()
        res = subprocess.run([PYTHON, str(script_path)], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        step_elapsed = time.perf_counter() - step_start

        if res.returncode != 0:
            print(f"❌ FAILED [{title}] after {step_elapsed:.2f}s:")
            print(res.stderr or res.stdout)
            sys.exit(1)
        else:
            print(f"✅ COMPLETED in {step_elapsed:.2f}s")
            # Print brief summary from stdout
            lines = [l for l in res.stdout.strip().splitlines() if l.strip()]
            for l in lines[-4:]:
                print(f"   {l}")

    total_time = time.perf_counter() - start_total
    print("\n" + "=" * 80)
    print(f"PIPELINE COMPLETED SUCCESSFULLY IN {total_time:.2f} SECONDS")
    print("=" * 80)


if __name__ == "__main__":
    run_pipeline()
