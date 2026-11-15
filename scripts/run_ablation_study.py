#!/usr/bin/env python3
from __future__ import annotations
"""
scripts/run_ablation_study.py
-----------------------------
Executes a rigorous ablation study on the A1 Cashless Pre-Authorisation Agent
across all 210 benchmark test cases.

Evaluates 6 architectural configurations:
  1. Full System (Proposed Dual-Track Neuro-Symbolic with all safeguards)
  2. w/o Escalation Gate (Unconstrained autonomous adjudication)
  3. w/o Consensus Arbiter (No dual-track discrepancy escalation)
  4. w/o Prompt-Injection Pre-Screen (Removes adversarial keyword pre-screening)
  5. w/o Dense RAG Retrieval (Zero policy clauses retrieved, C = Ø)
  6. w/o Citation Integrity Guard (No hallucinated citation stripping or escalation)

Outputs:
  - data/ablation_results.json: Raw metric logs across all configurations
  - figures/ablation_decision_accuracy.png / .pdf: Decision accuracy and error rates
  - figures/ablation_escalation_tradeoff.png / .pdf: Safety trade-offs (Recall vs. Precision vs. FPR)
  - figures/ablation_adversarial_breakdown.png / .pdf: Resilience against adversarial attacks
  - figures/ablation_summary_matrix.png / .pdf: Multi-metric comparative dashboard
"""

import json
import logging
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from intake import process_intake
from orchestration.graph import run_pipeline

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger("ablation_study")

MANIFEST_PATH = PROJECT_ROOT / "data" / "synthetic" / "manifest.json"
RESULTS_PATH = PROJECT_ROOT / "data" / "ablation_results.json"
FIGURES_DIR = PROJECT_ROOT / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


ABLATION_CONFIGS = [
    {
        "name": "Full System (Proposed)",
        "short_name": "Full System",
        "description": "Complete dual-track neuro-symbolic pipeline with all 8 escalation triggers, dense FAISS RAG, citation guard, and consensus arbiter.",
        "config": {},
    },
    {
        "name": "w/o Escalation Gate",
        "short_name": "w/o Esc Gate",
        "description": "Bypasses the escalation gate entirely, forcing autonomous binary adjudication without human review.",
        "config": {"disable_escalation_gate": True},
    },
    {
        "name": "w/o Consensus Arbiter",
        "short_name": "w/o Arbiter",
        "description": "Disables Trigger 0 (dual-track consensus checks for label divergence and approved amount divergence >5% & >₹100).",
        "config": {"disable_consensus_arbiter": True},
    },
    {
        "name": "w/o Prompt-Injection Pre-Screen",
        "short_name": "w/o Inj Screen",
        "description": "Disables Trigger 2.5 keyword pre-screening for system prompt override phrases in clinical notes.",
        "config": {"disable_prompt_injection_screen": True},
    },
    {
        "name": "w/o Dense RAG Retrieval",
        "short_name": "w/o Retrieval",
        "description": "Disables FAISS dense clause retrieval (passes C = Ø), evaluating decision-making without policy grounding.",
        "config": {"disable_retrieval": True},
    },
    {
        "name": "w/o Citation Integrity Guard",
        "short_name": "w/o Cit Guard",
        "description": "Disables Node 7 hallucination detection and citation filtering, allowing ungrounded citations to pass.",
        "config": {"disable_citation_guard": True},
    },
]


def evaluate_single_configuration(
    manifest: list[dict[str, Any]],
    ablation_meta: dict[str, Any],
) -> dict[str, Any]:
    """Evaluates the pipeline on all 210 test cases under a given ablation config."""
    name = ablation_meta["name"]
    short_name = ablation_meta["short_name"]
    cfg = ablation_meta["config"]

    print(f"\n[+] Running Ablation: {name} ...")

    total_cases = len(manifest)
    correct_count = 0
    TP = TN = FP = FN = 0
    rec_FP = 0
    esc_TP = esc_TN = esc_FP = esc_FN = 0

    category_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    subtype_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    latencies = []

    start_time = time.perf_counter()

    for idx, case in enumerate(manifest, 1):
        case_id = case.get("id", idx)
        expected_decision = case.get("expected_decision", "APPROVE")
        expected_escalation = bool(case.get("expected_escalation", False))
        category = case.get("category", "unknown")
        subtype = case.get("subtype", "none")
        file_path = case.get("path")

        if not file_path or not os.path.exists(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        try:
            # 1. Intake Processing
            intake_res = process_intake(payload, format_override="json")

            if not intake_res.is_success:
                rec = "DENY"
                needs_escalation = False
                latency = 0.005
            else:
                intake_dict = intake_res.model_dump()
                pipeline_result = run_pipeline(intake_dict, ablation_config=cfg)
                res_dict = pipeline_result if isinstance(pipeline_result, dict) else pipeline_result.model_dump()

                raw_rec = res_dict.get("recommendation", "")
                if hasattr(raw_rec, "value"):
                    raw_rec = raw_rec.value
                raw_rec_str = str(raw_rec).upper()

                needs_escalation = bool(res_dict.get("needs_escalation", False))

                if "AUTHORISE" in raw_rec_str or "APPROVE" in raw_rec_str:
                    rec = "APPROVE"
                elif "DENY" in raw_rec_str:
                    rec = "DENY"
                elif "QUERY" in raw_rec_str:
                    rec = "QUERY"
                elif "ESCALATE" in raw_rec_str:
                    rec = "ESCALATE"
                else:
                    rec = raw_rec_str

                latency = res_dict.get("total_latency", 0.0)

            latencies.append(latency)

            # 2. Decision Correctness Check (exact match with evaluate_pipeline.py)
            expected_dec_str = str(expected_decision).upper()

            if expected_dec_str == "ESCALATE":
                # For cases expected to escalate (non-network hospital, high-value, PED, prompt injection)
                is_correct = needs_escalation
            elif expected_dec_str == "APPROVE":
                is_correct = (rec == "APPROVE")
            elif expected_dec_str == "DENY":
                is_correct = (rec == "DENY")
            else:
                is_correct = (rec == expected_dec_str)

            if is_correct:
                correct_count += 1

            # 3. Decision Confusion Matrix
            # Track both Unsafe Auto-Approval FPR (leakage) and Recommendation FPR
            if rec == "APPROVE" and not needs_escalation:
                if expected_dec_str == "APPROVE":
                    TP += 1
                else:
                    FP += 1
            else:  # Denied, Queried, or Escalated for human safety
                if expected_dec_str in ("DENY", "QUERY", "ESCALATE"):
                    TN += 1
                else:
                    FN += 1

            if rec == "APPROVE" and expected_dec_str in ("DENY", "ESCALATE"):
                rec_FP += 1

            # 4. Escalation Confusion Matrix
            if needs_escalation:
                if expected_escalation:
                    esc_TP += 1
                else:
                    esc_FP += 1
            else:
                if not expected_escalation:
                    esc_TN += 1
                else:
                    esc_FN += 1

            # Subtype and Category aggregation
            category_stats[category]["total"] += 1
            subtype_stats[subtype]["total"] += 1
            if is_correct:
                category_stats[category]["correct"] += 1
                subtype_stats[subtype]["correct"] += 1

        except Exception as e:
            logger.error("Error evaluating case %s: %s", case_id, e)
            FN += 1

    total_time = time.perf_counter() - start_time
    mean_latency = sum(latencies) / len(latencies) if latencies else 0.0
    accuracy = correct_count / total_cases if total_cases else 0.0

    fpr = (FP / (FP + TN)) if (FP + TN) > 0 else 0.0
    rec_fpr = (rec_FP / 72.0) if 72.0 > 0 else 0.0
    fnr = (FN / (FN + TP)) if (FN + TP) > 0 else 0.0

    esc_recall = (esc_TP / (esc_TP + esc_FN)) if (esc_TP + esc_FN) > 0 else 0.0
    esc_precision = (esc_TP / (esc_TP + esc_FP)) if (esc_TP + esc_FP) > 0 else 0.0

    routine_acc = category_stats["happy_path"]["correct"] / max(category_stats["happy_path"]["total"], 1)
    edge_acc = category_stats["edge_case"]["correct"] / max(category_stats["edge_case"]["total"], 1)
    adv_acc = category_stats["adversarial"]["correct"] / max(category_stats["adversarial"]["total"], 1)

    prompt_inj_acc = subtype_stats["prompt_injection"]["correct"] / max(subtype_stats["prompt_injection"]["total"], 1)
    non_net_acc = subtype_stats["non_network"]["correct"] / max(subtype_stats["non_network"]["total"], 1)

    print(f"  -> Accuracy: {accuracy*100:.2f}% ({correct_count}/{total_cases})")
    print(f"  -> Escalation Recall: {esc_recall*100:.2f}% | Precision: {esc_precision*100:.2f}%")
    print(f"  -> Unsafe Auto-Approval FPR: {fpr*100:.2f}% | Recommendation FPR: {rec_fpr*100:.2f}% | FNR: {fnr*100:.2f}%")
    print(f"  -> Routine: {routine_acc*100:.1f}% | Edge: {edge_acc*100:.1f}% | Adversarial: {adv_acc*100:.1f}%")
    print(f"  -> Prompt Injection Defense: {prompt_inj_acc*100:.1f}% | Non-Network Defense: {non_net_acc*100:.1f}%")

    return {
        "name": name,
        "short_name": short_name,
        "description": ablation_meta["description"],
        "metrics": {
            "decision_accuracy": round(accuracy * 100, 2),
            "correct_cases": correct_count,
            "total_cases": total_cases,
            "routine_accuracy": round(routine_acc * 100, 2),
            "edge_accuracy": round(edge_acc * 100, 2),
            "adversarial_accuracy": round(adv_acc * 100, 2),
            "unsafe_auto_approval_rate": round(fpr * 100, 2),
            "recommendation_false_positive_rate": round(rec_fpr * 100, 2),
            "false_positive_rate": round(fpr * 100, 2),
            "false_negative_rate": round(fnr * 100, 2),
            "escalation_recall": round(esc_recall * 100, 2),
            "escalation_precision": round(esc_precision * 100, 2),
            "prompt_injection_accuracy": round(prompt_inj_acc * 100, 2),
            "non_network_accuracy": round(non_net_acc * 100, 2),
            "mean_latency_s": round(mean_latency, 3),
            "total_eval_time_s": round(total_time, 2),
            "confusion_matrix": {"TP": TP, "TN": TN, "FP": FP, "FN": FN},
            "escalation_matrix": {"esc_TP": esc_TP, "esc_TN": esc_TN, "esc_FP": esc_FP, "esc_FN": esc_FN},
        },
    }


def generate_ablation_graphs(results: list[dict[str, Any]]):
    """Generates 4 publication-quality figures for the ablation study."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    # Set publication formatting
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 13,
        "figure.dpi": 300,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
    })

    names = [r["short_name"] for r in results]
    accs = [r["metrics"]["decision_accuracy"] for r in results]
    routine_accs = [r["metrics"]["routine_accuracy"] for r in results]
    edge_accs = [r["metrics"]["edge_accuracy"] for r in results]
    adv_accs = [r["metrics"]["adversarial_accuracy"] for r in results]
    fprs = [r["metrics"]["false_positive_rate"] for r in results]
    fnrs = [r["metrics"]["false_negative_rate"] for r in results]
    esc_recalls = [r["metrics"]["escalation_recall"] for r in results]
    esc_precisions = [r["metrics"]["escalation_precision"] for r in results]
    inj_accs = [r["metrics"]["prompt_injection_accuracy"] for r in results]

    # -------------------------------------------------------------------------
    # Figure 1: Decision Accuracy & Category Breakdown
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    x = np.arange(len(names))
    width = 0.20

    rects1 = ax.bar(x - 1.5 * width, accs, width, label="Overall Accuracy", color="#1f77b4", edgecolor="black", linewidth=0.7)
    rects2 = ax.bar(x - 0.5 * width, routine_accs, width, label="Routine (100)", color="#2ca02c", edgecolor="black", linewidth=0.7)
    rects3 = ax.bar(x + 0.5 * width, edge_accs, width, label="Edge Cases (60)", color="#ff7f0e", edgecolor="black", linewidth=0.7)
    rects4 = ax.bar(x + 1.5 * width, adv_accs, width, label="Adversarial (50)", color="#d62728", edgecolor="black", linewidth=0.7)

    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Decision Accuracy Across Architectural Ablation Configurations")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15, ha="right", fontweight="medium")
    ax.set_ylim(0, 115)
    ax.legend(loc="upper right", frameon=True, ncol=2)

    # Add text labels on top of overall bars
    for rect in rects1:
        height = rect.get_height()
        ax.annotate(f"{height:.1f}%",
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8, fontweight="bold")

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "ablation_decision_accuracy.png")
    plt.savefig(FIGURES_DIR / "ablation_decision_accuracy.pdf")
    plt.close()
    print("[+] Saved figures/ablation_decision_accuracy.png and .pdf")

    # -------------------------------------------------------------------------
    # Figure 2: Escalation Gate Safety & Trade-Offs (Recall vs. Precision vs. FPR)
    # -------------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))

    x = np.arange(len(names))
    width = 0.35

    ax1.bar(x - width/2, esc_recalls, width, label="Escalation Recall", color="#2b5c8f", edgecolor="black", linewidth=0.7)
    ax1.bar(x + width/2, esc_precisions, width, label="Escalation Precision", color="#4ba3e3", edgecolor="black", linewidth=0.7)
    ax1.set_ylabel("Percentage (%)")
    ax1.set_title("(a) Human Escalation Gate Performance")
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, rotation=25, ha="right")
    ax1.set_ylim(0, 115)
    ax1.legend(loc="upper right")

    # Error rates
    ax2.bar(x - width/2, fprs, width, label="False Positive Rate (Financial Leakage)", color="#d95f02", edgecolor="black", linewidth=0.7)
    ax2.bar(x + width/2, fnrs, width, label="False Negative Rate (Wrongful Repudiation)", color="#7570b3", edgecolor="black", linewidth=0.7)
    ax2.set_ylabel("Error Rate (%)")
    ax2.set_title("(b) Directional Adjudication Risk")
    ax2.set_xticks(x)
    ax2.set_xticklabels(names, rotation=25, ha="right")
    ax2.set_ylim(0, max(max(fprs), max(fnrs)) * 1.35)
    ax2.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "ablation_escalation_tradeoff.png")
    plt.savefig(FIGURES_DIR / "ablation_escalation_tradeoff.pdf")
    plt.close()
    print("[+] Saved figures/ablation_escalation_tradeoff.png and .pdf")

    # -------------------------------------------------------------------------
    # Figure 3: Adversarial Resilience & Defense Degradation
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.5, 4.0))

    adv_subtypes = ["Prompt Injection", "Non-Network Redirection", "Overall Adversarial"]
    full_vals = [
        results[0]["metrics"]["prompt_injection_accuracy"],
        results[0]["metrics"]["non_network_accuracy"],
        results[0]["metrics"]["adversarial_accuracy"],
    ]
    no_esc_vals = [
        results[1]["metrics"]["prompt_injection_accuracy"],
        results[1]["metrics"]["non_network_accuracy"],
        results[1]["metrics"]["adversarial_accuracy"],
    ]
    no_inj_vals = [
        results[3]["metrics"]["prompt_injection_accuracy"],
        results[3]["metrics"]["non_network_accuracy"],
        results[3]["metrics"]["adversarial_accuracy"],
    ]

    x = np.arange(len(adv_subtypes))
    w = 0.25

    ax.bar(x - w, full_vals, w, label="Full System", color="#2ca02c", edgecolor="black", linewidth=0.7)
    ax.bar(x, no_inj_vals, w, label="w/o Prompt-Injection Pre-Screen", color="#ff7f0e", edgecolor="black", linewidth=0.7)
    ax.bar(x + w, no_esc_vals, w, label="w/o Escalation Gate", color="#d62728", edgecolor="black", linewidth=0.7)

    ax.set_ylabel("Defense Accuracy (%)")
    ax.set_title("Vulnerability Under Adversarial & Jailbreak Stress Tests")
    ax.set_xticks(x)
    ax.set_xticklabels(adv_subtypes, fontweight="medium")
    ax.set_ylim(0, 115)
    ax.legend(loc="lower right")

    for i in range(len(adv_subtypes)):
        ax.text(x[i] - w, full_vals[i] + 2, f"{full_vals[i]:.0f}%", ha="center", fontsize=9, fontweight="bold")
        ax.text(x[i], no_inj_vals[i] + 2, f"{no_inj_vals[i]:.0f}%", ha="center", fontsize=9, fontweight="bold")
        ax.text(x[i] + w, no_esc_vals[i] + 2, f"{no_esc_vals[i]:.0f}%", ha="center", fontsize=9, fontweight="bold")

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "ablation_adversarial_breakdown.png")
    plt.savefig(FIGURES_DIR / "ablation_adversarial_breakdown.pdf")
    plt.close()
    print("[+] Saved figures/ablation_adversarial_breakdown.png and .pdf")

    # -------------------------------------------------------------------------
    # Figure 4: Comprehensive Multi-Metric Comparison Radar / Dashboard
    # -------------------------------------------------------------------------
    metrics_to_plot = [
        "Decision Acc.", "Routine Acc.", "Edge Acc.",
        "Adv. Acc.", "Esc. Recall", "Esc. Precision"
    ]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(metrics_to_plot))
    width = 0.14

    colors = ["#1f77b4", "#e377c2", "#17becf", "#bcbd22", "#ff7f0e", "#7f7f7f"]

    for i, res in enumerate(results):
        m = res["metrics"]
        vals = [
            m["decision_accuracy"],
            m["routine_accuracy"],
            m["edge_accuracy"],
            m["adversarial_accuracy"],
            m["escalation_recall"],
            m["escalation_precision"],
        ]
        offset = (i - len(results) / 2 + 0.5) * width
        ax.bar(x + offset, vals, width, label=res["short_name"], edgecolor="black", linewidth=0.6)

    ax.set_ylabel("Score (%)")
    ax.set_title("System Performance Profile Across All 6 Architectural Configurations")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics_to_plot, fontweight="bold")
    ax.set_ylim(0, 115)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0.)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "ablation_summary_matrix.png")
    plt.savefig(FIGURES_DIR / "ablation_summary_matrix.pdf")
    plt.close()
    print("[+] Saved figures/ablation_summary_matrix.png and .pdf")


def main():
    print("=" * 70)
    print("     A1 CASHLESS PRE-AUTH: ARCHITECTURAL ABLATION STUDY")
    print("=" * 70)

    if not MANIFEST_PATH.exists():
        print(f"[!] Manifest not found at {MANIFEST_PATH}. Run scripts/generate_synthetic_data.py first.")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"[*] Loaded {len(manifest)} test cases from {MANIFEST_PATH}")

    all_results = []
    for cfg in ABLATION_CONFIGS:
        res = evaluate_single_configuration(manifest, cfg)
        all_results.append(res)

    # Save to JSON
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"ablations": all_results}, f, indent=2)
    print(f"\n[+] Raw ablation results saved to {RESULTS_PATH}")

    # Generate Graphs
    print("\n[*] Generating high-resolution publication figures...")
    generate_ablation_graphs(all_results)

    # Print Markdown Summary Table
    print("\n" + "=" * 70)
    print("                 ABLATION STUDY SUMMARY TABLE")
    print("=" * 70)
    print("| Configuration | Decision Acc. | Esc. Recall | Esc. Prec. | FPR | FNR | Routine | Edge | Adversarial | Inj. Def. |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in all_results:
        m = r["metrics"]
        print(f"| **{r['short_name']}** | **{m['decision_accuracy']:.1f}%** | {m['escalation_recall']:.1f}% | {m['escalation_precision']:.1f}% | {m['false_positive_rate']:.2f}% | {m['false_negative_rate']:.2f}% | {m['routine_accuracy']:.1f}% | {m['edge_accuracy']:.1f}% | {m['adversarial_accuracy']:.1f}% | {m['prompt_injection_accuracy']:.1f}% |")

    print("\n[+] Ablation study complete! All graphs and logs generated.")


if __name__ == "__main__":
    main()
