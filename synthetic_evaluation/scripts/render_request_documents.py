"""
synthetic_evaluation/scripts/render_request_documents.py
--------------------------------------------------------
Phase 5 Renderer: Renders all 300 test cases into 6 multi-format document variants:
  1. JSON (format_variants/json/TC-xxx.json)
  2. TXT (format_variants/txt/TC-xxx.txt)
  3. Digital PDF (format_variants/pdf/TC-xxx.pdf)
  4. Microsoft Word DOCX (format_variants/docx/TC-xxx.docx)
  5. Scanned PNG Image (format_variants/png/TC-xxx.png)
  6. Scanned JPEG Image (format_variants/jpg/TC-xxx.jpg)

Applies controlled OCR distortions for the 25 OCR stress cases (TC-256 to TC-280):
  - Gaussian blur
  - Low-resolution downsampling & upscaling
  - Rotation / Skew (3–6 degrees)
  - Noise speckles
  - Contrast fading / low illumination
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

from docx import Document as DocxDocument
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def format_request_as_text(data: dict[str, Any]) -> str:
    """Formats a pre-auth dictionary into structured plain text representation."""
    patient = data.get("patient", {})
    policy = data.get("policy", {})
    hosp = data.get("hospital", {})
    diag = data.get("diagnosis", {})
    proc = data.get("procedure", {})
    cost = data.get("cost_estimate", {})

    lines = [
        "A1 CASHLESS HEALTH INSURANCE PRE-AUTHORISATION FORM",
        "--------------------------------------------------",
        f"Request ID: {data.get('request_id')}",
        f"Submission Date: {data.get('submitted_at')}",
        f"Admission Date: {data.get('admission_date')}",
        f"Source Format: {data.get('source_format')}",
        "",
        "PATIENT DETAILS",
        "---------------",
        f"Full Name: {patient.get('full_name')}",
        f"Age: {patient.get('age')}",
        f"Gender: {patient.get('gender')}",
        f"Policy / Member Number: {patient.get('policy_number')}",
        "",
        "POLICY DETAILS",
        "--------------",
        f"Policy Number: {policy.get('policy_number')}",
        f"Plan Type: {policy.get('plan_type')}",
        f"Sum Insured: INR {policy.get('sum_insured')}",
        f"Policy Inception Date: {policy.get('policy_start_date')}",
        f"Co-Payment Percentage: {policy.get('co_pay_pct', '0.00')}%",
        "",
        "HOSPITAL & CLINICAL DETAILS",
        "---------------------------",
        f"Hospital Name: {hosp.get('name')}",
        f"Network Status: {hosp.get('network_tier')}",
        f"Facility Category: {hosp.get('facility_category')}",
        f"City: {hosp.get('city')}, State: {hosp.get('state')}",
        f"ICD-10 Code: {diag.get('icd10_code')}",
        f"Primary Diagnosis: {diag.get('description')}",
        f"Pre-Existing Disease Flag: {diag.get('is_pre_existing')}",
        f"Planned Procedure: {proc.get('description')}",
        f"Procedure Code: {proc.get('procedure_code')}",
        f"Admission Type: {proc.get('admission_type')}",
        "",
        "ESTIMATED COST BREAKDOWN",
        "------------------------",
    ]

    for item in cost.get("line_items", []):
        lines.append(f"  [{item.get('category', 'miscellaneous'):<14}] {item.get('item', ''):<45}: INR {item.get('amount')}")

    lines.extend([
        "------------------------",
        f"Total Estimated Amount: INR {cost.get('total_amount')}",
        "",
        "TREATING PHYSICIAN CLINICAL NOTES",
        "---------------------------------",
        data.get("clinical_notes", "Nil documented notes."),
        "==================================================",
    ])
    return "\n".join(lines)


def render_request_pdf(data: dict[str, Any], out_path: Path):
    """Render pre-auth form as a standardized digital PDF."""
    doc = SimpleDocTemplate(str(out_path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("T", parent=styles["Heading1"], fontSize=13, leading=16, textColor=colors.HexColor("#1A365D"), alignment=1)
    sub_style = ParagraphStyle("S", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#4A5568"), alignment=1)
    h2_style = ParagraphStyle("H", parent=styles["Heading2"], fontSize=9, leading=12, textColor=colors.HexColor("#2B6CB0"), spaceBefore=6, spaceAfter=3)
    c_style = ParagraphStyle("C", parent=styles["Normal"], fontSize=8, leading=10)

    pat = data.get("patient", {})
    pol = data.get("policy", {})
    hosp = data.get("hospital", {})
    diag = data.get("diagnosis", {})
    proc = data.get("procedure", {})
    cost = data.get("cost_estimate", {})

    story = [
        Paragraph("<b>A1 CASHLESS HEALTH INSURANCE PRE-AUTHORISATION FORM</b>", title_style),
        Paragraph(f"Request ID: {data.get('request_id')} | Submitted: {data.get('submitted_at')} | Network: {hosp.get('network_tier')}", sub_style),
        Spacer(1, 8),
        Paragraph("1. Patient & Policy Demographics", h2_style),
    ]

    t1_data = [
        [Paragraph("<b>Patient Name</b>", c_style), Paragraph(str(pat.get("full_name")), c_style), Paragraph("<b>Age / Gender</b>", c_style), Paragraph(f"{pat.get('age')} Y / {pat.get('gender')}", c_style)],
        [Paragraph("<b>Policy Number</b>", c_style), Paragraph(str(pol.get("policy_number")), c_style), Paragraph("<b>Plan Type</b>", c_style), Paragraph(str(pol.get("plan_type")), c_style)],
        [Paragraph("<b>Sum Insured</b>", c_style), Paragraph(f"INR {pol.get('sum_insured')}", c_style), Paragraph("<b>Co-Pay Ratio</b>", c_style), Paragraph(f"{pol.get('co_pay_pct', '0.00')}%", c_style)],
    ]
    t1 = Table(t1_data, colWidths=[100, 170, 100, 170])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t1)

    story.append(Paragraph("2. Clinical & Treatment Details", h2_style))
    t2_data = [
        [Paragraph("<b>Hospital</b>", c_style), Paragraph(str(hosp.get("name")), c_style), Paragraph("<b>Admission Date</b>", c_style), Paragraph(str(data.get("admission_date")), c_style)],
        [Paragraph("<b>Diagnosis</b>", c_style), Paragraph(f"{diag.get('description')} ({diag.get('icd10_code')})", c_style), Paragraph("<b>PED Flag</b>", c_style), Paragraph("Yes" if diag.get("is_pre_existing") else "No", c_style)],
        [Paragraph("<b>Procedure</b>", c_style), Paragraph(f"{proc.get('description')} ({proc.get('procedure_code')})", c_style), Paragraph("<b>Admission Type</b>", c_style), Paragraph(str(proc.get("admission_type")), c_style)],
    ]
    t2 = Table(t2_data, colWidths=[100, 170, 100, 170])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EDF2F7")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t2)

    story.append(Paragraph("3. Itemised Cost Estimates", h2_style))
    cost_rows = [[Paragraph("<b>Billing Item Description</b>", c_style), Paragraph("<b>Category</b>", c_style), Paragraph("<b>Amount (INR)</b>", c_style)]]
    for it in cost.get("line_items", [])[:8]:
        cost_rows.append([Paragraph(it.get("item", ""), c_style), Paragraph(it.get("category", ""), c_style), Paragraph(f"INR {it.get('amount')}", c_style)])
    cost_rows.append([Paragraph("<b>TOTAL ESTIMATED AMOUNT</b>", c_style), Paragraph("", c_style), Paragraph(f"<b>INR {cost.get('total_amount')}</b>", c_style)])

    t3 = Table(cost_rows, colWidths=[270, 130, 140])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t3)

    doc.build(story)


def render_request_docx(data: dict[str, Any], out_path: Path):
    """Render pre-auth form as Microsoft Word document."""
    doc = DocxDocument()
    t = doc.add_heading("CASHLESS PRE-AUTHORISATION REQUEST", level=0)
    t.runs[0].font.color.rgb = RGBColor(26, 54, 93)

    pat = data.get("patient", {})
    pol = data.get("policy", {})
    hosp = data.get("hospital", {})
    diag = data.get("diagnosis", {})
    cost = data.get("cost_estimate", {})

    doc.add_paragraph(f"Request ID: {data.get('request_id')} | Hospital: {hosp.get('name')}")

    doc.add_heading("Patient & Policy Summary", level=1)
    table = doc.add_table(rows=4, cols=2)
    table.style = "Table Grid"
    rows = [
        ("Patient Name", str(pat.get("full_name"))),
        ("Age / Gender", f"{pat.get('age')} Y / {pat.get('gender')}"),
        ("Policy Number", str(pol.get("policy_number"))),
        ("Sum Insured (INR)", f"₹ {pol.get('sum_insured')}"),
    ]
    for i, (k, v) in enumerate(rows):
        table.cell(i, 0).text = k
        table.cell(i, 1).text = v

    doc.add_heading("Clinical & Billing Estimate", level=1)
    doc.add_paragraph(f"Diagnosis: {diag.get('description')} ({diag.get('icd10_code')})")
    doc.add_paragraph(f"Total Hospital Claim: ₹ {cost.get('total_amount')}")

    doc.save(str(out_path))


def render_request_image(data: dict[str, Any], out_path: Path, distortion: str | None = None, img_format: str = "PNG"):
    """Render pre-auth form as a 1200x800 image, optionally applying controlled OCR distortions."""
    img = Image.new("RGB", (1200, 800), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Document border
    draw.rectangle([15, 15, 1185, 785], outline=(30, 41, 59), width=2)
    draw.rectangle([25, 25, 1175, 75], fill=(241, 245, 249))
    draw.text((45, 40), "CASHLESS HEALTH INSURANCE PRE-AUTHORISATION FORM", fill=(15, 23, 42))

    pat = data.get("patient", {})
    pol = data.get("policy", {})
    hosp = data.get("hospital", {})
    diag = data.get("diagnosis", {})
    proc = data.get("procedure", {})
    cost = data.get("cost_estimate", {})

    y = 95
    draw.text((45, y), f"REQUEST ID: {data.get('request_id')} | SUBMITTED: {data.get('submitted_at')}", fill=(100, 116, 139))
    y += 35

    # Patient info
    draw.text((45, y), "PATIENT & POLICY INFORMATION", fill=(30, 58, 138))
    draw.line([45, y + 20, 1150, y + 20], fill=(203, 213, 224), width=1)
    y += 30
    draw.text((45, y), f"Patient Name : {pat.get('full_name')}", fill=(30, 41, 59))
    draw.text((650, y), f"Policy No.   : {pol.get('policy_number')}", fill=(30, 41, 59))
    y += 25
    draw.text((45, y), f"Age / Gender : {pat.get('age')} / {pat.get('gender')}", fill=(30, 41, 59))
    draw.text((650, y), f"Sum Insured  : INR {pol.get('sum_insured')}", fill=(30, 41, 59))
    y += 35

    # Hospital & Clinical
    draw.text((45, y), "HOSPITAL & CLINICAL DIAGNOSIS", fill=(30, 58, 138))
    draw.line([45, y + 20, 1150, y + 20], fill=(203, 213, 224), width=1)
    y += 30
    draw.text((45, y), f"Hospital Name: {hosp.get('name')}", fill=(30, 41, 59))
    draw.text((650, y), f"Network Tier : {hosp.get('network_tier')}", fill=(30, 41, 59))
    y += 25
    draw.text((45, y), f"Diagnosis    : {diag.get('description')} ({diag.get('icd10_code')})", fill=(30, 41, 59))
    draw.text((650, y), f"Admission    : {data.get('admission_date')}", fill=(30, 41, 59))
    y += 25
    draw.text((45, y), f"Procedure    : {proc.get('description')}", fill=(30, 41, 59))
    y += 35

    # Financial breakdown
    draw.text((45, y), "ESTIMATED BILLING HEADS", fill=(30, 58, 138))
    draw.line([45, y + 20, 1150, y + 20], fill=(203, 213, 224), width=1)
    y += 30
    for item in cost.get("line_items", [])[:5]:
        draw.text((60, y), f"• {item.get('item', ''):<45} : INR {item.get('amount')}", fill=(51, 65, 85))
        y += 25

    y += 10
    draw.line([45, y, 1150, y], fill=(30, 41, 59), width=2)
    y += 15
    draw.text((45, y), f"TOTAL ESTIMATED CLAIM AMOUNT: INR {cost.get('total_amount')}", fill=(15, 23, 42))

    # Apply controlled distortions if specified
    if distortion == "gaussian_blur":
        img = img.filter(ImageFilter.GaussianBlur(radius=2.0))
    elif distortion == "downsample_low_res":
        w, h = img.size
        img = img.resize((w // 4, h // 4), Image.Resampling.BILINEAR)
        img = img.resize((w, h), Image.Resampling.NEAREST)
    elif distortion == "rotation_skew":
        img = img.rotate(4.5, expand=False, fillcolor=(255, 255, 255))
    elif distortion == "contrast_fade":
        enh = ImageEnhance.Contrast(img)
        img = enh.enhance(0.4)
        bri = ImageEnhance.Brightness(img)
        img = bri.enhance(0.8)
    elif distortion == "noise_speckle":
        # Add random salt-and-pepper noise
        noise_draw = ImageDraw.Draw(img)
        random.seed(42)
        for _ in range(3000):
            nx = random.randint(0, 1199)
            ny = random.randint(0, 799)
            noise_draw.point((nx, ny), fill=(0, 0, 0))

    img.save(str(out_path), format=img_format)


def render_all_request_documents(base_dir: Path):
    """Render all 300 test cases into 6 document formats."""
    canonical_cases_dir = base_dir / "canonical_cases"
    case_files = sorted(canonical_cases_dir.glob("TC-*.json"))

    json_dir = base_dir / "format_variants" / "json"
    txt_dir = base_dir / "format_variants" / "txt"
    pdf_dir = base_dir / "format_variants" / "pdf"
    docx_dir = base_dir / "format_variants" / "docx"
    png_dir = base_dir / "format_variants" / "png"
    jpg_dir = base_dir / "format_variants" / "jpg"

    for d in [json_dir, txt_dir, pdf_dir, docx_dir, png_dir, jpg_dir]:
        d.mkdir(parents=True, exist_ok=True)

    counts = {"json": 0, "txt": 0, "pdf": 0, "docx": 0, "png": 0, "jpg": 0}

    for cf in case_files:
        with open(cf, "r", encoding="utf-8") as f:
            cdata = json.load(f)

        cid = cdata["test_case_id"]
        payload = cdata["payload"]
        distortion = cdata.get("ocr_distortion")

        # 1. JSON
        with open(json_dir / f"{cid}.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        counts["json"] += 1

        # 2. TXT
        txt_str = format_request_as_text(payload)
        with open(txt_dir / f"{cid}.txt", "w", encoding="utf-8") as f:
            f.write(txt_str)
        counts["txt"] += 1

        # 3. PDF
        render_request_pdf(payload, pdf_dir / f"{cid}.pdf")
        counts["pdf"] += 1

        # 4. DOCX
        render_request_docx(payload, docx_dir / f"{cid}.docx")
        counts["docx"] += 1

        # 5. PNG
        render_request_image(payload, png_dir / f"{cid}.png", distortion=distortion, img_format="PNG")
        counts["png"] += 1

        # 6. JPG
        render_request_image(payload, jpg_dir / f"{cid}.jpg", distortion=distortion, img_format="JPEG")
        counts["jpg"] += 1

    print("\n--- REQUEST DOCUMENT RENDERING COMPLETE ---")
    for fmt, cnt in counts.items():
        print(f"  {fmt.upper():<6}: {cnt} files rendered")
    print(f"Total Request Artifacts: {sum(counts.values())} files across 6 formats")


def main():
    base_dir = PROJECT_ROOT / "synthetic_evaluation"
    render_all_request_documents(base_dir)


if __name__ == "__main__":
    main()
