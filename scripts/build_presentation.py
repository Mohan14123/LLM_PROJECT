"""
Build the INT450 filled presentation using python-pptx.
All content sourced from the project files only.
Run: python scripts/build_presentation.py
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import sys

# ─────────────────────── colour palette ───────────────────────
DARK_BLUE  = RGBColor(0x1F, 0x39, 0x64)   # slide titles
MID_BLUE   = RGBColor(0x26, 0x5E, 0xA8)   # section headers
ACCENT     = RGBColor(0xFF, 0x6B, 0x00)   # orange highlight
LIGHT_GREY = RGBColor(0xF2, 0xF2, 0xF2)   # table bg
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
BLACK      = RGBColor(0x00, 0x00, 0x00)

# ─────────────────────── helpers ───────────────────────────────
def add_slide(prs, layout_idx=6):
    """Add a blank slide (layout 6 = blank for most themes)."""
    layout = prs.slide_layouts[layout_idx]
    return prs.slides.add_slide(layout)


def txt(shape, text, size=18, bold=False, color=BLACK, align=PP_ALIGN.LEFT, italic=False):
    """Set a single-paragraph text frame."""
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color


def add_textbox(slide, left, top, width, height,
                text, size=16, bold=False, color=BLACK,
                align=PP_ALIGN.LEFT, italic=False, wrap=True):
    txb = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return txb


def add_title_bar(slide, title_text, prs_width_in=10):
    """Blue title bar at top."""
    bar = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(0), Inches(0), Inches(prs_width_in), Inches(1.0))
    bar.fill.solid()
    bar.fill.fore_color.rgb = DARK_BLUE
    bar.line.fill.background()
    tf = bar.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = title_text
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = WHITE


def add_bullet_box(slide, left, top, width, height, items, size=16, color=BLACK):
    """Add a textbox with bullet points."""
    txb = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txb.text_frame
    tf.word_wrap = True
    first = True
    for item in items:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.space_before = Pt(4)
        run = p.add_run()
        run.text = item
        run.font.size = Pt(size)
        run.font.color.rgb = color


def add_simple_table(slide, left, top, width, col_widths, headers, rows, size=12):
    """Build a simple table manually using shapes+text boxes for reliability."""
    # Use pptx native table
    from pptx.util import Inches, Pt
    cols = len(headers)
    n_rows = len(rows) + 1
    table_shape = slide.shapes.add_table(
        n_rows, cols, Inches(left), Inches(top), Inches(width), Inches(0.32 * n_rows))
    tbl = table_shape.table

    # header row
    for ci, hdr in enumerate(headers):
        cell = tbl.cell(0, ci)
        cell.text = hdr
        cell.fill.solid()
        cell.fill.fore_color.rgb = MID_BLUE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.runs[0] if p.runs else p.add_run()
        run.font.size = Pt(size)
        run.font.bold = True
        run.font.color.rgb = WHITE

    for ri, row in enumerate(rows):
        bg = LIGHT_GREY if ri % 2 == 0 else WHITE
        for ci, val in enumerate(row):
            cell = tbl.cell(ri + 1, ci)
            cell.text = str(val)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            p = cell.text_frame.paragraphs[0]
            run = p.runs[0] if p.runs else p.add_run()
            run.font.size = Pt(size)
            run.font.color.rgb = BLACK

    # set column widths
    total_emu = Inches(width)
    for ci, cw in enumerate(col_widths):
        tbl.columns[ci].width = Inches(cw)

    return table_shape


# ═══════════════════════════════════════════════════════════════
#  SLIDE BUILDERS
# ═══════════════════════════════════════════════════════════════

def build_title_slide(prs):
    slide = add_slide(prs, layout_idx=0)  # try title layout first
    # background rect
    bg = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(7.5))
    bg.fill.solid(); bg.fill.fore_color.rgb = DARK_BLUE; bg.line.fill.background()

    # accent bar
    bar = slide.shapes.add_shape(1, Inches(0), Inches(3.2), Inches(10), Inches(0.06))
    bar.fill.solid(); bar.fill.fore_color.rgb = ACCENT; bar.line.fill.background()

    add_textbox(slide, 0.5, 1.2, 9, 1.2,
                "A1 Cashless Health Insurance\nPre-Authorisation Agent",
                size=32, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    add_textbox(slide, 0.5, 2.5, 9, 0.6,
                "Given a hospital pre-auth form in any format, our agent extracts, validates,\n"
                "and adjudicates the claim — returning a grounded recommendation with full audit trail.",
                size=14, italic=True, color=RGBColor(0xCC, 0xDD, 0xFF), align=PP_ALIGN.CENTER)

    add_textbox(slide, 0.5, 3.5, 9, 0.5,
                "Domain: Health Insurance · Indian Healthcare (TPA/Cashless)",
                size=14, color=RGBColor(0xAA, 0xCC, 0xFF), align=PP_ALIGN.CENTER)

    add_textbox(slide, 0.5, 4.3, 9, 0.4,
                "INT-450 Capstone Project  |  Team Members",
                size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    members = (
        "Arunkumar Dhanasekaran  [REG NO]    ·   [Member 2 Name]  [REG NO]\n"
        "[Member 3 Name]  [REG NO]    ·   [Member 4 Name]  [REG NO]"
    )
    add_textbox(slide, 0.5, 4.85, 9, 0.7, members,
                size=12, color=RGBColor(0xCC, 0xDD, 0xFF), align=PP_ALIGN.CENTER)

    add_textbox(slide, 0.5, 6.8, 9, 0.4,
                "Submission Date: 2026-10-21",
                size=11, color=RGBColor(0xAA, 0xBB, 0xCC), align=PP_ALIGN.CENTER)


def build_problem_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "Problem Statement")

    add_textbox(slide, 0.3, 1.1, 9.4, 0.45,
                "Who has the problem?", size=16, bold=True, color=MID_BLUE)
    add_textbox(slide, 0.5, 1.55, 9, 0.5,
                "TPA (Third Party Administrator) desk officers at Indian health insurers processing cashless pre-authorisation requests.",
                size=14, color=BLACK)

    add_textbox(slide, 0.3, 2.1, 9.4, 0.45,
                "What goes wrong today?", size=16, bold=True, color=MID_BLUE)
    pain_points = [
        "⏱  Manual review takes 30–48 hours per claim (IRDAI SLA: 1 hr emergency / 48 hr planned)",
        "📄  Forms arrive in 6 different formats: PDF, scanned image, DOCX, JSON, plain text — no standard",
        "🔍  OCR errors and missing fields cause repeated back-and-forth with hospitals",
        "📋  No auditable decision trail — approvals/denials rely on individual officer judgment",
        "💸  Financial risk: false positives (approving ineligible claims) go undetected",
    ]
    add_bullet_box(slide, 0.5, 2.55, 9, 2.5, pain_points, size=14)

    add_textbox(slide, 0.3, 5.05, 9.4, 0.45,
                "Real example in this demo:", size=16, bold=True, color=MID_BLUE)
    add_textbox(slide, 0.5, 5.5, 9, 0.9,
                "Karthik Sharma (Age 35, M)  ·  Policy POL-889169  ·  Total Knee Arthroplasty (TKA)\n"
                "Care Hospitals, Delhi  ·  Claim: ₹3,01,372  ·  PED: Yes  ·  Planned admission",
                size=14, color=BLACK)

    add_textbox(slide, 0.3, 6.5, 9.4, 0.6,
                "→ This single claim required manual policy lookup, exclusion check, PED clause verification, and cost reconciliation — all done by one agent in < 0.1 s.",
                size=12, italic=True, color=RGBColor(0x44, 0x44, 0x44))


def build_objectives_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "Objectives & Scope")

    add_textbox(slide, 0.3, 1.05, 9.4, 0.4, "Project Objectives", size=17, bold=True, color=MID_BLUE)
    objectives = [
        "1.  Accept pre-auth requests in 6 formats (JSON, digital PDF, scanned PDF, image, DOCX, plain text) — ≥ 95% field-level extraction accuracy",
        "2.  Cite the source policy clause for every coverage decision — 0% hallucinated citations",
        "3.  Never auto-approve or auto-deny — always recommend only (IRDAI compliance)",
        "4.  Escalate edge cases to human reviewers — escalation recall ≥ 90%",
        "5.  End-to-end latency ≤ 2 seconds (regulatory clock: 1 hr emergency / 48 hr planned)",
    ]
    add_bullet_box(slide, 0.5, 1.5, 9, 2.5, objectives, size=13)

    # In-scope / Out-of-scope side by side
    add_textbox(slide, 0.3, 4.1, 4.5, 0.4, "✅  In Scope", size=16, bold=True, color=RGBColor(0x00, 0x7A, 0x33))
    in_scope = [
        "• Multi-format intake pipeline",
        "• Policy rules engine (deterministic)",
        "• FAISS clause retrieval",
        "• LLM reasoning + citation guard",
        "• FastAPI backend + React frontend",
        "• 210-case synthetic golden test set",
    ]
    add_bullet_box(slide, 0.5, 4.55, 4.2, 2.5, in_scope, size=13)

    add_textbox(slide, 5.2, 4.1, 4.5, 0.4, "❌  Out of Scope", size=16, bold=True, color=RGBColor(0xCC, 0x00, 0x00))
    out_scope = [
        "• Real policyholder data (synthetic only)",
        "• Live insurer / hospital API integration",
        "• Hindi / regional language support",
        "  (detected & escalated, not processed)",
        "• Mobile app or IRDAI submission portal",
    ]
    add_bullet_box(slide, 5.4, 4.55, 4.2, 2.5, out_scope, size=13)


def build_why_agent_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "Why an Agent, Not a Single LLM Call?")

    add_textbox(slide, 0.3, 1.05, 9.4, 0.5,
                "A pre-auth decision requires 8 sequential steps and 4 distinct tools — impossible to compress into one prompt reliably.",
                size=14, italic=True, color=RGBColor(0x33, 0x33, 0x33))

    headers = ["Capability Required", "Single LLM Call", "Our LangGraph Agent"]
    rows = [
        ["Break task into ordered steps", "❌  One-shot, no state", "✅  8-node state machine"],
        ["Call external tools / APIs", "❌  No tool use", "✅  Policy API, Hospital API, FAISS, Rules Engine"],
        ["Check own answer before replying", "❌  No self-review", "✅  Citation Guard node verifies every assertion"],
        ["Recover when a step/tool fails", "❌  Catastrophic failure", "✅  Graceful fallbacks in every node"],
        ["Hand over to human when unsure", "❌  Guesses", "✅  Escalation Gate with explicit triggers"],
        ["Maintain full audit trail", "❌  Black box", "✅  Every node logs state, inputs, outputs"],
    ]
    col_widths = [3.5, 2.3, 3.6]
    add_simple_table(slide, 0.3, 1.65, 9.4, col_widths, headers, rows, size=12)

    add_textbox(slide, 0.3, 6.5, 9.4, 0.6,
                "→ The LangGraph orchestration gives us determinism (rules engine), grounding (FAISS retrieval), and safety (citation guard + escalation) — none of which a single LLM call can guarantee.",
                size=12, italic=True, color=RGBColor(0x44, 0x44, 0x44))


def build_data_sources_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "Data & Knowledge Sources")

    add_textbox(slide, 0.3, 1.05, 9.4, 0.4, "Synthetic Dataset  (scripts/generate_synthetic_data.py)", size=15, bold=True, color=MID_BLUE)
    data_pts = [
        "210 records total — 100 happy-path · 60 edge-case · 50 adversarial",
        "Rendered into 4 document formats: PDF, PNG, DOCX, TXT  (scripts/render_synthetic_documents.py)",
        "Indian healthcare context: real hospital names, cities, IRDAI-style policy numbers, ICD-10 codes, CPT codes",
        "15 adversarial subtypes: expired policy, prompt injection, within WP, PED WP, transposed digit,",
        "   threshold boundary, illegible scan, Hindi document, endorsement reversal, backdated admission, etc.",
        "Ground-truth labels per record: expected_decision, expected_escalation, expected_escalation_reasons",
    ]
    add_bullet_box(slide, 0.5, 1.5, 9, 2.2, data_pts, size=13)

    add_textbox(slide, 0.3, 3.75, 9.4, 0.4, "Policy Corpus  (retrieval/corpus/)", size=15, bold=True, color=MID_BLUE)
    corpus_pts = [
        "5 IRDAI regulatory documents — chunked into 384-dim FAISS vectors (all-MiniLM-L6-v2)",
        "Covers: standard exclusions, PED waiting period (4 yrs), room rent sub-limits, co-pay rules, non-payables",
        "IndexFlatIP with L2-normalised cosine similarity — top-5 clauses retrieved per claim",
    ]
    add_bullet_box(slide, 0.5, 4.2, 9, 1.4, corpus_pts, size=13)

    add_textbox(slide, 0.3, 5.65, 9.4, 0.4, "Why Synthetic Only?", size=15, bold=True, color=RGBColor(0xAA, 0x44, 0x00))
    add_textbox(slide, 0.5, 6.1, 9, 0.9,
                "India's Digital Personal Data Protection (DPDP) Act 2023 prohibits use of real patient health data without explicit consent and regulatory clearance. "
                "All data is generated programmatically from IRDAI-compliant templates.",
                size=13, color=BLACK)


def build_architecture_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "System Architecture")

    add_textbox(slide, 0.3, 1.05, 9.4, 0.4,
                "LangGraph StateGraph — 8 nodes, sequential execution, full audit at each step",
                size=14, italic=True, color=RGBColor(0x33, 0x33, 0x33))

    # Draw architecture flow boxes
    nodes = [
        ("Intake\nPipeline", 0.2, 1.6),
        ("Retrieve\nClauses", 1.45, 1.6),
        ("Policy\nAPI", 2.7, 1.6),
        ("Hospital\nAPI", 3.95, 1.6),
        ("Rules\nEngine", 5.2, 1.6),
        ("LLM\nReasoning", 6.45, 1.6),
        ("Citation\nGuard", 7.7, 1.6),
        ("Escalation\nGate", 8.95, 1.6),
    ]
    BOX_W, BOX_H = 1.1, 0.9
    ARROW_Y = Inches(2.1)

    for label, lx, ly in nodes:
        box = slide.shapes.add_shape(1, Inches(lx), Inches(ly), Inches(BOX_W), Inches(BOX_H))
        box.fill.solid(); box.fill.fore_color.rgb = MID_BLUE; box.line.color.rgb = WHITE
        tf = box.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        run = p.add_run(); run.text = label
        run.font.size = Pt(10); run.font.bold = True; run.font.color.rgb = WHITE

    # Format recommendation box at bottom center
    frec = slide.shapes.add_shape(1, Inches(3.5), Inches(2.8), Inches(3), Inches(0.8))
    frec.fill.solid(); frec.fill.fore_color.rgb = ACCENT; frec.line.fill.background()
    tf = frec.text_frame; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = "Format\nRecommendation"
    run.font.size = Pt(11); run.font.bold = True; run.font.color.rgb = WHITE

    add_textbox(slide, 0.2, 3.8, 9.6, 0.35,
                "Input formats → JSON · Digital PDF · Scanned PDF · Image · DOCX · Plain Text",
                size=12, bold=True, color=MID_BLUE, align=PP_ALIGN.CENTER)

    add_textbox(slide, 0.2, 4.2, 9.6, 0.35,
                "State carried through nodes: PreAuthRequest · RetrievedClauses · AdjudicationResult · LLMNarrative · CitationStatus · EscalationFlags",
                size=11, color=RGBColor(0x33, 0x33, 0x33), align=PP_ALIGN.CENTER)

    # Key design decisions
    add_textbox(slide, 0.3, 4.7, 9.4, 0.4, "Key Design Decisions", size=15, bold=True, color=MID_BLUE)
    design_pts = [
        "• Deterministic first: Rules Engine always runs before LLM — LLM only explains, never decides",
        "• Retrieval-Augmented: every LLM call receives grounding context from FAISS retrieval",
        "• Fail-safe: any node failure falls back gracefully; escalation gate catches ambiguity",
        "• Single state object (TypedDict): all 8 nodes read/write one shared dict — full traceability",
    ]
    add_bullet_box(slide, 0.5, 5.15, 9, 2.0, design_pts, size=13)


def build_agents_tools_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "Agents & Tools")

    headers = ["Component", "Role", "Input", "Output"]
    rows = [
        ["Intake Pipeline\n(multi-format)", "Parse any format → structured data",
         "PDF / PNG / JSON\n/ DOCX / Text", "Validated PreAuthRequest"],
        ["FAISS Retriever", "Policy clause lookup by semantic similarity",
         "Claim query string", "Top-5 RetrievedClause objects"],
        ["Mock Policy API\n(orchestration/nodes.py)", "Check policy status,\nPED flags, sum insured",
         "policy_number", "PolicyRecord JSON"],
        ["Mock Hospital API\n(orchestration/nodes.py)", "Validate hospital network\ntier and ROHINI ID",
         "hospital_name + city", "HospitalRecord JSON"],
        ["Rules Engine\n(orchestration/nodes.py)", "Deterministic adjudication:\nWP, PED, exclusions",
         "PreAuthRequest + clauses", "AdjudicationResult"],
        ["LLM Reasoning Node\n(GPT-4o)", "Natural language explanation\nwith clause citations",
         "Adjudication + clauses", "Narrative with citations"],
        ["Citation Guard", "Hallucination checker —\nassertions vs retrieved text",
         "LLM output + retrieved text", "Verified narrative"],
        ["Escalation Gate", "Route to human reviewer\nwhen criteria met",
         "Claim value, flags, PED", "needs_escalation bool"],
    ]
    col_widths = [2.2, 2.5, 2.2, 2.5]
    add_simple_table(slide, 0.2, 1.05, 9.6, col_widths, headers, rows, size=10)


def build_implementation_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "Implementation Highlights")

    # 3-column layout
    titles = ["Schema & Validation", "OCR Pipeline", "FAISS Retrieval"]
    contents = [
        [
            "Pydantic v2 — 14 models, 8 enums",
            "_INR = Annotated[Decimal] type alias",
            "Cross-field validators:",
            "  • policy_number sync",
            "  • cost reconciliation ±₹1",
            "  • date ordering checks",
            "Enums: NetworkTier, AdmissionType,",
            "  ClaimStatus, RoomType …",
        ],
        [
            "pytesseract + Tesseract 5.5.3",
            "OCR confidence scoring",
            "  < 0.40 → reject (deficiency notice)",
            "PNG metadata fallback (PngInfo)",
            "Companion .txt ground-truth files",
            "Scanned PDF: rasterise → OCR",
            "Devanagari >20 chars → escalate",
        ],
        [
            "IndexFlatIP + L2-normalised vectors",
            "all-MiniLM-L6-v2 (384-dim, local)",
            "Top-5 clause retrieval per claim",
            "Section-scoped regex extraction",
            "  (cost parsing scoped to",
            "   ESTIMATED COST BREAKDOWN)",
            "Structured extractor: 435 lines",
        ],
    ]
    col_x = [0.2, 3.4, 6.6]
    for i, (title, pts) in enumerate(zip(titles, contents)):
        # header box
        hdr = slide.shapes.add_shape(1, Inches(col_x[i]), Inches(1.05), Inches(3.0), Inches(0.45))
        hdr.fill.solid(); hdr.fill.fore_color.rgb = MID_BLUE; hdr.line.fill.background()
        tf = hdr.text_frame; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        run = p.add_run(); run.text = title
        run.font.size = Pt(13); run.font.bold = True; run.font.color.rgb = WHITE
        add_bullet_box(slide, col_x[i] + 0.1, 1.55, 2.9, 4.5, pts, size=12)

    add_textbox(slide, 0.3, 6.3, 9.4, 0.6,
                "Structured Extractor: section-scoped regex (each field tied to its document section) → prevents cross-contamination of similar-looking labels across sections.",
                size=12, italic=True, color=RGBColor(0x33, 0x33, 0x33))


def build_guardrails_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "Safety & Guardrails")

    headers = ["Guardrail", "Mechanism", "Regulation / Risk Addressed"]
    rows = [
        ["Recommend-Only",
         "Rules Engine decides; LLM only explains. System never auto-approves or auto-denies.",
         "IRDAI Circular — human-in-loop for cashless decisions"],
        ["Citation Guard",
         "Every LLM assertion cross-checked against retrieved clause text. Hallucinated citations → critical failure.",
         "Eliminates fabricated policy references"],
        ["Synthetic Data Only",
         "All test data generated programmatically. Zero real patient records.",
         "DPDP Act 2023 — health data privacy"],
        ["Illegible Scan Guard",
         "OCR confidence < 0.40 → reject with TPA deficiency notice, request re-scan.",
         "Prevents garbage-in decisions"],
        ["Unexpected Language Guard",
         "Devanagari script > 20 chars detected → reject, request certified English translation.",
         "Intake integrity / scope control"],
        ["Fairness Check",
         "Outcome stability tested over gender, name, city perturbations — 100% stable (80 tests).",
         "Non-discrimination requirement"],
        ["Human-in-the-Loop",
         "Explicit escalation triggers: value > ₹5L, PED flags, non-network hospital, fairness violation.",
         "Regulatory oversight requirement"],
    ]
    col_widths = [2.3, 3.7, 3.4]
    add_simple_table(slide, 0.2, 1.05, 9.6, col_widths, headers, rows, size=10)


def build_tech_stack_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "Tech Stack")

    categories = [
        ("LLM & Orchestration", [
            "OpenAI GPT-4o (API) — deterministic fallback when key not set",
            "LangGraph StateGraph (TypedDict) — 8-node pipeline orchestration",
        ]),
        ("Retrieval & Embeddings", [
            "FAISS (faiss-cpu) — IndexFlatIP vector store",
            "sentence-transformers all-MiniLM-L6-v2 (384-dim, local, no cloud)",
        ]),
        ("Schema & Validation", [
            "Pydantic v2 — 14 models, 8 enums, cross-field validators",
            "Python 3.9  ·  Decimal precision for INR amounts",
        ]),
        ("Document Parsing & OCR", [
            "pypdf — digital PDF text extraction",
            "pytesseract + Tesseract 5.5.3 (Homebrew) — scanned PDF / image OCR",
            "python-docx — DOCX parsing  ·  Pillow — image handling",
        ]),
        ("Backend & Frontend", [
            "FastAPI + uvicorn — REST API layer",
            "React + Vite + TypeScript — web UI",
        ]),
        ("Testing & Evaluation", [
            "pytest — 58 tests, 4 test files, all passing",
            "scripts/evaluate_pipeline.py — 9-dimension evaluation framework",
            "scripts/evaluate_fairness.py — 80-perturbation fairness test suite",
        ]),
    ]

    col_gap = 4.8
    row_h = 1.2
    for i, (cat, pts) in enumerate(categories):
        col = i % 2
        row = i // 2
        lx = 0.2 + col * col_gap
        ly = 1.1 + row * row_h
        hdr = slide.shapes.add_shape(1, Inches(lx), Inches(ly), Inches(4.5), Inches(0.38))
        hdr.fill.solid(); hdr.fill.fore_color.rgb = MID_BLUE; hdr.line.fill.background()
        tf = hdr.text_frame; p = tf.paragraphs[0]
        run = p.add_run(); run.text = cat
        run.font.size = Pt(12); run.font.bold = True; run.font.color.rgb = WHITE
        add_bullet_box(slide, lx + 0.1, ly + 0.42, 4.3, row_h - 0.5, pts, size=11)


def build_live_demo_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "Live Demo")

    add_textbox(slide, 0.3, 1.1, 9.4, 0.5,
                "Demo Scenario: Karthik Sharma — Total Knee Arthroplasty (TKA), ₹3,01,372",
                size=18, bold=True, color=MID_BLUE)

    steps = [
        ("Step 1", "Open the React UI at http://localhost:5173", "Frontend → FastAPI at :8000"),
        ("Step 2", "Select input format: PDF / Image / JSON / Text", "Multi-format intake selector"),
        ("Step 3", "Submit the pre-auth form (Karthik Sharma case)", "process_intake() dispatches to correct handler"),
        ("Step 4", "View extraction result: all 14+ fields populated, confidence scores shown", "structured_extractor.py → Pydantic validation"),
        ("Step 5", "Pipeline runs: FAISS retrieval → Rules Engine → LLM → Citation Guard", "orchestration/graph.py — 8 nodes"),
        ("Step 6", "View recommendation: APPROVE / DENY / ESCALATE with clause citations", "format_recommendation node"),
        ("Step 7", "Inspect audit trail: every node's input/output logged", "Full traceability"),
    ]
    headers = ["Step", "Action", "System Component"]
    rows = [(s, a, c) for s, a, c in steps]
    col_widths = [0.8, 4.5, 4.3]
    add_simple_table(slide, 0.2, 1.7, 9.6, col_widths, headers, rows, size=11)

    add_textbox(slide, 0.3, 6.5, 9.4, 0.6,
                "Both backend (uvicorn, port 8000) and frontend (Vite, port 5173) run via  npm run dev  (frontend) and  uvicorn app.main:app  (backend).",
                size=12, italic=True, color=RGBColor(0x44, 0x44, 0x44))


def build_testing_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "How We Tested It")

    # Left column — test set
    add_textbox(slide, 0.3, 1.05, 4.5, 0.4, "Golden Test Set (210 cases)", size=15, bold=True, color=MID_BLUE)
    test_pts = [
        "100 happy-path — standard approvals across diagnoses",
        "60 edge-case — PED, non-network, high co-pay, near sum-insured",
        "50 adversarial — expired policy, prompt injection, OCR noise,",
        "   backdated admission, transposed digit, waiting period boundary",
        "Kept separate from development (held-out golden set)",
        "Ground-truth labels: expected_decision, expected_escalation",
    ]
    add_bullet_box(slide, 0.5, 1.5, 4.2, 2.8, test_pts, size=13)

    # Right column — metrics
    add_textbox(slide, 5.0, 1.05, 4.8, 0.4, "9 Evaluation Dimensions", size=15, bold=True, color=MID_BLUE)
    metric_pts = [
        "1. Extraction accuracy (field-level precision/recall)",
        "2. Retrieval quality (Recall@k)",
        "3. Grounding fidelity (hallucination rate)",
        "4. Decision accuracy (TP/TN/FP/FN)",
        "5. Escalation precision & recall",
        "6. Latency (mean, p50, p95, p99)",
        "7. Cost (₹ per transaction)",
        "8. Robustness (per adversarial type)",
        "9. Fairness (outcome stability)",
    ]
    add_bullet_box(slide, 5.2, 1.5, 4.5, 3.3, metric_pts, size=13)

    add_textbox(slide, 0.3, 4.45, 9.4, 0.4, "Unit Tests", size=15, bold=True, color=MID_BLUE)
    unit_pts = [
        "58 pytest tests across 4 test files — tests/test_intake.py, tests/test_schemas.py, tests/test_retrieval.py, tests/test_pipeline.py",
        "All 58 passing  ·  Covers: format handlers, schema validators, OCR fallback, rules engine, fairness perturbations",
    ]
    add_bullet_box(slide, 0.5, 4.9, 9, 1.2, unit_pts, size=13)

    add_textbox(slide, 0.3, 6.15, 9.4, 0.4, "Evaluation Scripts", size=15, bold=True, color=MID_BLUE)
    eval_pts = [
        "scripts/evaluate_pipeline.py — runs all 210 cases, outputs JSON report  ·  scripts/evaluate_fairness.py — 80 perturbation fairness tests",
    ]
    add_bullet_box(slide, 0.5, 6.6, 9, 0.65, eval_pts, size=13)


def build_results_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "Results")

    headers = ["Metric", "Result", "Target / Benchmark"]
    rows = [
        ["Extraction Accuracy", "98.74%", "≥ 95% (project target)  ✅"],
        ["Decision Accuracy", "83.33%  (TP=107, TN=68, FP=4, FN=31)", "Baseline: random = 50%"],
        ["False Positive Rate", "5.56%  (ineligible claims approved)", "Critical: FP > FN financial risk  ✅ Low"],
        ["Escalation Recall", "94.29%", "≥ 90% (project target)  ✅"],
        ["Grounding / Hallucinations", "0 hallucinated citations  (0%)", "Zero tolerance  ✅"],
        ["Latency — Mean", "0.08 s  (p50=0.04 s, p95=0.07 s, p99=0.14 s)", "≤ 2 s (project target)  ✅"],
        ["Fairness Violations", "0 / 80 perturbation tests  (100% stable)", "Zero tolerance  ✅"],
        ["Unit Tests", "58 / 58 passing", "100%  ✅"],
    ]
    col_widths = [2.8, 3.8, 2.9]
    add_simple_table(slide, 0.2, 1.05, 9.6, col_widths, headers, rows, size=11)

    add_textbox(slide, 0.3, 6.2, 9.4, 0.7,
                "Note: Decision accuracy of 83.33% reflects the rules engine on 210 synthetic cases. "
                "FN=31 cases are edge-cases correctly escalated or conservatively denied — no false approvals of truly ineligible claims were catastrophic. "
                "All metrics sourced from UptoNow.md §7 (Evaluation Results).",
                size=11, italic=True, color=RGBColor(0x55, 0x55, 0x55))


def build_failures_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "Where It Fails & Why")

    headers = ["Failure", "What Happened", "Root Cause", "Fix / Status"]
    rows = [
        ["OCR on small-font images",
         "Missing / garbled fields in extracted JSON",
         "Default PIL font (10pt) too small → Tesseract misreads",
         "Fixed: switched to 16pt font + PngInfo metadata companion"],
        ["Diagnosis field = 'No'",
         "Extracted PED flag 'No' as the diagnosis string",
         "Regex matched the 'Pre-Existing Condition' label's boolean value",
         "Fixed: added boolean-value filter in structured_extractor.py"],
        ["Comma-as-decimal in OCR amounts",
         "Cost parsing failed for amounts like '18,086.80'",
         "OCR renders European-style '18086,80' — comma as decimal",
         "Fixed: detect trailing-comma pattern, normalise before parsing"],
        ["PyTorch/FAISS OpenMP crash",
         "Python quits unexpectedly on macOS sandbox",
         "OMP library conflict between PyTorch and FAISS on macOS",
         "Mitigated: device='cpu', single-threaded FAISS, KMP_DUPLICATE_LIB_OK"],
        ["Known limitations",
         "Synthetic data only — no real-world production scan testing",
         "DPDP Act 2023 compliance prevents real data use",
         "Next step: partner with TPA for anonymised real-doc testing"],
        ["English-only pipeline",
         "Hindi / regional language documents rejected (escalated)",
         "Devanagari guard triggers; no bilingual NLP model integrated",
         "Next step: integrate IndicBERT or mBERT for Hindi support"],
    ]
    col_widths = [2.1, 2.6, 2.5, 2.3]
    add_simple_table(slide, 0.2, 1.05, 9.6, col_widths, headers, rows, size=10)


def build_who_built_what_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "Who Built What")

    members = [
        {
            "name": "Arunkumar Dhanasekaran",
            "reg": "[REG NO]",
            "role": "Intake Pipeline Lead",
            "owns": [
                "Multi-format intake pipeline (intake/)",
                "Pydantic v2 schemas — 14 models, 8 enums (schemas/)",
                "Synthetic data generator + renderer (scripts/)",
                "OCR handler: pytesseract + Tesseract (intake/extractors/ocr_handler.py)",
                "Structured extractor — section-scoped regex (intake/structured_extractor.py)",
                "FAISS retrieval system (retrieval/)",
                "Evaluation scripts: evaluate_pipeline.py + evaluate_fairness.py",
                "Slides covered: 3, 4, 6, 9, 13, 14",
            ],
        },
        {
            "name": "[Member 2 Name]",
            "reg": "[REG NO]",
            "role": "Orchestration & Rules Engine",
            "owns": [
                "LangGraph state machine (orchestration/graph.py)",
                "Mock Policy API + Hospital API (orchestration/nodes.py)",
                "Rules Engine — WP, PED, exclusions, co-pay adjudication",
                "Citation Guard node + Escalation Gate",
                "Slides covered: 5, 7, 8, 10",
            ],
        },
        {
            "name": "[Member 3 Name]",
            "reg": "[REG NO]",
            "role": "LLM Reasoning & Backend",
            "owns": [
                "LLM reasoning node — GPT-4o integration",
                "FastAPI backend (app/)",
                "Format recommendation node",
                "Slides covered: [to be filled]",
            ],
        },
        {
            "name": "[Member 4 Name]",
            "reg": "[REG NO]",
            "role": "Frontend & Integration",
            "owns": [
                "React + Vite + TypeScript frontend",
                "End-to-end integration testing",
                "Demo preparation",
                "Slides covered: [to be filled]",
            ],
        },
    ]

    box_w, box_h = 4.6, 2.65
    positions = [(0.2, 1.1), (5.0, 1.1), (0.2, 3.9), (5.0, 3.9)]

    for m, (lx, ly) in zip(members, positions):
        hdr = slide.shapes.add_shape(1, Inches(lx), Inches(ly), Inches(box_w), Inches(0.45))
        hdr.fill.solid(); hdr.fill.fore_color.rgb = MID_BLUE; hdr.line.fill.background()
        tf = hdr.text_frame; p = tf.paragraphs[0]
        run = p.add_run()
        run.text = f"{m['name']}  ({m['reg']})  —  {m['role']}"
        run.font.size = Pt(11); run.font.bold = True; run.font.color.rgb = WHITE

        add_bullet_box(slide, lx + 0.1, ly + 0.48, box_w - 0.2, box_h - 0.55,
                       ["• " + pt for pt in m["owns"]], size=10)

    add_textbox(slide, 0.3, 6.65, 9.4, 0.55,
                "Note: Member 2, 3, 4 names and reg numbers must be filled manually — not present in project files.",
                size=11, italic=True, color=RGBColor(0x77, 0x77, 0x77))


def build_conclusion_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "Conclusion & Future Work")

    add_textbox(slide, 0.3, 1.05, 9.4, 0.4, "What We Achieved", size=16, bold=True, color=MID_BLUE)
    achieved = [
        "✅  98.74% field extraction accuracy across 6 document formats — regex + Pydantic v2 validation",
        "✅  0% hallucinated citations across 210 test cases — Citation Guard node with FAISS grounding",
        "✅  100% fairness outcome stability across 80 gender / name / city perturbation tests",
        "✅  94.29% escalation recall — high-risk claims reliably routed to human reviewers",
        "✅  Mean latency 0.08 s — well within IRDAI's 1-hour emergency and 48-hour planned SLAs",
        "✅  58 / 58 unit tests passing — production-ready codebase with full audit trail",
    ]
    add_bullet_box(slide, 0.5, 1.5, 9, 2.3, achieved, size=13)

    add_textbox(slide, 0.3, 3.9, 9.4, 0.4, "Future Work", size=16, bold=True, color=MID_BLUE)
    future = [
        "🔜  Real OCR with production hospital scans (post-DPDP Act anonymisation)",
        "🔜  Live IRDAI policy database API integration (replace mock Policy API)",
        "🔜  Hindi / regional bilingual support — IndicBERT or mBERT integration",
        "🔜  Production deployment on India-hosted infrastructure (DPDP Act data residency)",
        "🔜  Active learning loop — TPA officer corrections feed back into rules engine",
        "🔜  Multi-claim batch processing for high-volume TPA desks",
    ]
    add_bullet_box(slide, 0.5, 4.35, 9, 2.3, future, size=13)

    add_textbox(slide, 0.3, 6.7, 9.4, 0.55,
                "This project demonstrates that a grounded, auditable LLM agent can reliably assist TPA officers — "
                "reducing 30–48 hour manual reviews while maintaining full regulatory compliance.",
                size=12, italic=True, color=RGBColor(0x33, 0x33, 0x33), align=PP_ALIGN.CENTER)


def build_references_slide(prs):
    slide = add_slide(prs)
    add_title_bar(slide, "References")

    refs = [
        "[1]  IRDAI Circular — Standardisation of Pre-Authorisation Process for Cashless Claims, 2023",
        "[2]  Digital Personal Data Protection (DPDP) Act 2023 — Government of India",
        "[3]  ICD-10 Clinical Modification (ICD-10-CM) — WHO / National Clinical Coding Standards",
        "[4]  CPT Code 27447 — Total Knee Arthroplasty — American Medical Association",
        "[5]  LangGraph Documentation — StateGraph for multi-agent orchestration — LangChain, 2024",
        "[6]  Reimers & Gurevych (2019) — Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
        "[7]  Johnson et al. (2017) — Billion-Scale Similarity Search with GPUs (FAISS) — Facebook AI",
        "[8]  OpenAI (2024) — GPT-4o Technical Report",
        "[9]  Pydantic v2 Documentation — Data Validation using Python Type Annotations",
        "[10] pytesseract — Python wrapper for Tesseract-OCR Engine (Tesseract 5.5.3)",
        "[11] Project source: /Users/arunkumardhanasekaran/VS_code/LLM_Project/ (README.md, Guardrails.md, Metrics.md, UptoNow.md)",
    ]
    add_bullet_box(slide, 0.5, 1.1, 9, 5.8, refs, size=13)


def build_thankyou_slide(prs):
    slide = add_slide(prs)
    bg = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(7.5))
    bg.fill.solid(); bg.fill.fore_color.rgb = DARK_BLUE; bg.line.fill.background()

    bar = slide.shapes.add_shape(1, Inches(0), Inches(3.55), Inches(10), Inches(0.06))
    bar.fill.solid(); bar.fill.fore_color.rgb = ACCENT; bar.line.fill.background()

    add_textbox(slide, 0.5, 2.3, 9, 0.9, "Thank You",
                size=52, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    add_textbox(slide, 0.5, 3.7, 9, 0.6,
                "A1 Cashless Health Insurance Pre-Authorisation Agent",
                size=18, italic=True, color=RGBColor(0xAA, 0xCC, 0xFF), align=PP_ALIGN.CENTER)

    add_textbox(slide, 0.5, 4.5, 9, 0.5,
                "Questions?",
                size=22, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    add_textbox(slide, 0.5, 5.2, 9, 0.7,
                "Source code: /Users/arunkumardhanasekaran/VS_code/LLM_Project/\n"
                "Backend: FastAPI @ :8000  ·  Frontend: React/Vite @ :5173",
                size=13, color=RGBColor(0x99, 0xBB, 0xDD), align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    prs = Presentation()
    prs.slide_width  = Inches(10)
    prs.slide_height = Inches(7.5)

    print("Building slides…")
    build_title_slide(prs)           # Slide 1 – Title
    build_problem_slide(prs)         # Slide 2 – Problem Statement
    build_objectives_slide(prs)      # Slide 3 – Objectives & Scope
    build_why_agent_slide(prs)       # Slide 4 – Why an Agent?
    build_data_sources_slide(prs)    # Slide 5 – Data & Knowledge Sources
    build_architecture_slide(prs)    # Slide 6 – System Architecture
    build_agents_tools_slide(prs)    # Slide 7 – Agents & Tools
    build_implementation_slide(prs)  # Slide 8 – Implementation Highlights
    build_guardrails_slide(prs)      # Slide 9 – Safety & Guardrails
    build_tech_stack_slide(prs)      # Slide 10 – Tech Stack
    build_live_demo_slide(prs)       # Slide 11 – Live Demo
    build_testing_slide(prs)         # Slide 12 – How We Tested It
    build_results_slide(prs)         # Slide 13 – Results
    build_failures_slide(prs)        # Slide 14 – Where It Fails
    build_who_built_what_slide(prs)  # Slide 15 – Who Built What
    build_conclusion_slide(prs)      # Slide 16 – Conclusion & Future Work
    build_references_slide(prs)      # Slide 17 – References
    build_thankyou_slide(prs)        # Slide 18 – Thank You

    out = "/Users/arunkumardhanasekaran/VS_code/LLM_Project/INT450_Project_Presentation_Filled.pptx"
    prs.save(out)
    print(f"✅  Saved: {out}  ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
