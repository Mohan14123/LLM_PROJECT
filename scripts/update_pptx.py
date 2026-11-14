import sys
import traceback
from pptx import Presentation
from pptx.util import Pt

def update_text_run(p, new_text):
    """Safely update paragraph text while keeping font formatting."""
    if p.runs:
        font_name = p.runs[0].font.name
        font_size = p.runs[0].font.size
        font_bold = p.runs[0].font.bold
        font_italic = p.runs[0].font.italic
        
        # safely read color
        rgb = None
        try:
            rgb = p.runs[0].font.color.rgb
        except Exception:
            pass

        p.text = new_text
        if p.runs:
            p.runs[0].font.name = font_name
            p.runs[0].font.size = font_size
            p.runs[0].font.bold = font_bold
            p.runs[0].font.italic = font_italic
            if rgb is not None:
                try:
                    p.runs[0].font.color.rgb = rgb
                except Exception:
                    pass
    else:
        p.text = new_text

def update_cell_text(cell, new_text):
    if cell.text_frame.paragraphs:
        update_text_run(cell.text_frame.paragraphs[0], new_text)
        for extra in cell.text_frame.paragraphs[1:]:
            extra.text = ""
    else:
        cell.text = new_text

def main():
    prs = Presentation("LLM.pptx")
    print("Loaded LLM.pptx")

    # --- Slide 4 (index 3): Why an agent ---
    print("Updating Slide 4...")
    s4 = prs.slides[3]
    tbl4 = s4.shapes[4].table
    update_cell_text(tbl4.rows[1].cells[2], "✓ 9-node LangGraph StateGraph with Dual-Track Consensus")
    update_cell_text(tbl4.rows[3].cells[2], "✓ Citation Guard + Consensus Arbiter (cross-checks Rules vs. LLM Clinical)")

    sh7 = s4.shapes[7].text_frame
    update_text_run(sh7.paragraphs[0], "Dual-Track Neuro-Symbolic: Symbolic Rules (Track 1) and Neural Clinical LLM (Track 2) run in tandem.")
    update_text_run(sh7.paragraphs[1], "Consensus Arbiter cross-checks both decision concordance and financial amount concordance.")
    update_text_run(sh7.paragraphs[2], "Divergence triggers human escalation; compliant with IRDAI's human-in-the-loop requirement.")

    update_text_run(s4.shapes[9].text_frame.paragraphs[0], "Our reason in one line:  a pre-auth decision requires 8 sequential steps, 4 distinct tools, and dual-track consensus — impossible to compress into one prompt reliably.")

    # --- Slide 5 (index 4): Data sources ---
    print("Updating Slide 5...")
    s5 = prs.slides[4]
    tf13 = s5.shapes[13].text_frame
    font_name = tf13.paragraphs[0].runs[0].font.name
    font_color = tf13.paragraphs[0].runs[0].font.color.rgb

    corpus_lines = [
        "Corpus: 35 synthetic policy & regulatory documents across 4 categories:",
        "• 15 Policy Wordings & Clinical Guidelines (7 plan types + 8 procedure guidelines: Dialysis, Cataract, Knee, STEMI, etc.)",
        "• 8 Insurer Policy Schedules (Star Health, HDFC ERGO, Care, ICICI Lombard, Bajaj Allianz, Niva Bupa, New India, United)",
        "• 8 IRDAI Circulars (Master Circular 2024, Exclusions, Non-Payables, Cashless Timelines, Fraud, Grievance, Portability)",
        "• 4 Benefit & Tariff Schedules (Disease Sub-limits, Waiting Period Matrix, Co-pay Schedule, Room Rent Schedule)",
        "Indexing & Search: 384-dim embeddings (all-MiniLM-L6-v2) → FAISS IndexFlatIP (cosine similarity) → Top-5 clause retrieval",
    ]
    tf13.clear()
    for idx, line in enumerate(corpus_lines):
        p = tf13.add_paragraph() if idx > 0 else tf13.paragraphs[0]
        p.text = line
        p.font.name = font_name
        p.font.size = Pt(8.5)
        p.font.color.rgb = font_color
        p.space_after = Pt(2)

    # --- Slide 6 (index 5): System architecture ---
    print("Updating Slide 6...")
    s6 = prs.slides[5]
    update_text_run(s6.shapes[4].text_frame.paragraphs[0], "LangGraph StateGraph — 8 nodes with Dual-Track Neuro-Symbolic Consensus")
    update_text_run(s6.shapes[14].text_frame.paragraphs[1], "Track 1 (Symbolic): WP check, exclusions, room rent & procedure sub-limits")
    update_text_run(s6.shapes[16].text_frame.paragraphs[1], "Track 2 (Neural): Clinical necessity adjudication + machine tags")
    update_text_run(s6.shapes[20].text_frame.paragraphs[1], "Consensus Arbiter: routes to human on decision/amount divergence (>5%) or high-value")
    update_text_run(s6.shapes[44].text_frame.paragraphs[0], "Dual-Track Consensus: Rules engine and LLM evaluate in tandem; Arbiter flags any decision or amount discrepancy")

    # --- Slide 7 (index 6): Agents & Tools ---
    print("Updating Slide 7...")
    s7 = prs.slides[6]
    tbl7 = s7.shapes[4].table
    update_cell_text(tbl7.rows[5].cells[0], "Rules Engine — Track 1 (orchestration/nodes.py)")
    update_cell_text(tbl7.rows[5].cells[1], "Deterministic adjudication: WP, room rent & procedure sub-limits (Dialysis, Cataract)")
    update_cell_text(tbl7.rows[6].cells[0], "LLM Adjudicator — Track 2 (orchestration/nodes.py)")
    update_cell_text(tbl7.rows[6].cells[1], "Independent clinical necessity adjudication with clause citations & machine tags")
    update_cell_text(tbl7.rows[6].cells[3], "Clinical narrative + structured machine tags (CLINICAL_RECOMMENDATION, CLINICAL_APPROVED_AMOUNT)")
    update_cell_text(tbl7.rows[8].cells[0], "Escalation Gate & Arbiter (orchestration/nodes.py)")
    update_cell_text(tbl7.rows[8].cells[1], "Consensus Arbiter: check decision & financial amount agreement; route to human if diverged")

    # --- Slide 9 (index 8): Safety & Guardrails ---
    print("Updating Slide 9...")
    s9 = prs.slides[8]
    sh13 = s9.shapes[13].text_frame
    update_text_run(sh13.paragraphs[0], "Recommend-only rule: auto-approval/denial is never done. System output is always labelled RECOMMENDATION; a human TPA officer makes final decision (IRDAI compliance)")
    update_text_run(sh13.paragraphs[1], "Consensus & Escalation triggers: Dual-track discrepancy (decision or approved amount mismatch >5%), claim >₹5L, PED, non-network — code rule in escalation_gate")

    sh23 = s9.shapes[23].text_frame
    update_text_run(sh23.paragraphs[0], "Dual-track consensus divergence (rules vs LLM clinical mismatch or amount mismatch >5%)")

    # --- Slide 10 (index 9): Tech stack ---
    print("Updating Slide 10...")
    s10 = prs.slides[9]
    tbl10 = s10.shapes[4].table
    update_cell_text(tbl10.rows[3].cells[2], "Local, no cloud dependency; L2-normalised cosine similarity; fast on 35-doc knowledge corpus")
    update_cell_text(tbl10.rows[9].cells[2], "Fast HMR loop; real-time metrics, itemized deductions, history persistence, Dual-Track consensus badge")
    update_cell_text(tbl10.rows[10].cells[1], "pytest (62 tests, 5 files)")
    update_cell_text(tbl10.rows[10].cells[2], "Standard; added consensus arbiter & sub-limit suites; all 62 passing (100%)")

    # --- Slide 11 (index 10): How we tested it ---
    print("Updating Slide 11...")
    s11 = prs.slides[10]
    update_text_run(s11.shapes[19].text_frame.paragraphs[0], "62 pytest tests across 5 test files (test_intake.py, test_schemas.py, test_retrieval.py, test_pipeline.py, test_consensus_arbiter.py) — 62 / 62 passing")

    # --- Slide 12 (index 11): Results ---
    print("Updating Slide 12...")
    s12 = prs.slides[11]
    update_text_run(s12.shapes[29].text_frame.paragraphs[1], "Unit tests: 62 / 62 passing (100%  ✅)")

    # --- Slide 13 (index 12): Where it fails & why ---
    print("Updating Slide 13...")
    s13 = prs.slides[12]
    tbl13 = s13.shapes[4].table
    update_cell_text(tbl13.rows[4].cells[3], "Fixed: strict single-thread CPU isolation (OMP_NUM_THREADS=1, TOKENIZERS_PARALLELISM=false, KMP_DUPLICATE_LIB_OK=TRUE)")
    update_cell_text(tbl13.rows[5].cells[0], "Procedure sub-limit under-capping (Hemodialysis)")
    update_cell_text(tbl13.rows[5].cells[1], "Rules engine approved 100% (₹29,921) while LLM clinical summary noted ₹2,000 cap")
    update_cell_text(tbl13.rows[5].cells[2], "Rules previously only checked daily room rent; Arbiter only checked recommendation labels, not amounts")
    update_cell_text(tbl13.rows[5].cells[3], "Fixed: implemented procedure sub-limits in rules/sub_limits.py (dialysis ₹2,000 / cataract ₹40,000); Arbiter detects amount divergence")

    # --- Slide 14 (index 13): Conclusion ---
    print("Updating Slide 14...")
    s14 = prs.slides[13]
    tf7 = s14.shapes[7].text_frame
    p_new = tf7.add_paragraph()
    p_new.text = "4. Dual-Track Neuro-Symbolic Consensus — Combined deterministic IRDAI/tariff rules with independent neural clinical adjudication; automated Arbiter prevents financial amount and coverage discrepancies."
    if tf7.paragraphs[0].runs:
        run0 = tf7.paragraphs[0].runs[0]
        if p_new.runs:
            p_new.runs[0].font.name = run0.font.name
            p_new.runs[0].font.size = run0.font.size

    prs.save("LLM.pptx")
    print("Saved updated LLM.pptx successfully!")

if __name__ == "__main__":
    main()
