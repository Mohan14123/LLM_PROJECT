"""
synthetic_evaluation/scripts/render_policy_documents.py
------------------------------------------------------
Phase 2 Renderer: Renders all 35 synthetic insurance policies into:
  - Structured JSON (policies/json/)
  - Formatted Text (policies/txt/)
  - Professional Digital PDF (policies/pdf/)
  - Microsoft Word DOCX (policies/docx/)
  - Raster PNG Schedule (policies/png/)
  - Raster JPEG Schedule (policies/jpg/)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from docx import Document as DocxDocument
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def format_policy_as_text(p: dict[str, Any]) -> str:
    """Format canonical policy into a realistic, legally structured insurance policy wording document."""
    lines = [
        "=" * 80,
        f"{p['insurer_name'].upper()}",
        f"CERTIFICATE OF INSURANCE & POLICY SCHEDULE: {p['policy_name'].upper()}",
        f"UIN: {p.get('product_uin', 'N/A')} | Version: {p.get('product_version', '2024.1')}",
        "=" * 80,
        "",
        "SECTION 1: POLICY SCHEDULE & ENTITLEMENT DETAILS",
        "-" * 80,
        f"Policy Identifier      : {p['policy_id']}",
        f"Insurance Product Name : {p['policy_name']}",
        f"Underwriting Insurer   : {p['insurer_name']}",
        f"Plan Category / Type   : {p['policy_type'].upper()}",
        f"Policy Inception Date  : {p['policy_start_date']}",
        f"Policy Expiry Date     : {p['policy_expiry_date']}",
        f"Annual Sum Insured     : INR {p['sum_insured']['amount']}",
        f"Available Sum Insured  : INR {p['available_sum_insured']['amount']}",
        "",
        "SECTION 2: ROOM RENT & INTENSIVE CARE UNIT (ICU) RESTRICTIONS",
        "-" * 80,
        f"Room Rent Limit Type   : {p['room_rent_limits'].get('type', 'actuals')}",
        f"Daily Room Rent Cap    : INR {p['room_rent_limits'].get('daily_cap_inr') or 'No Cap / Actuals'}",
        f"Proportional Deduction : {'Applicable under Clause 3.1.A' if p['room_rent_limits'].get('proportional_deduction_applies') else 'Not Applicable'}",
        f"ICU Daily Limit        : INR {p['icu_limits'].get('daily_cap_inr') or 'No Cap / Actuals'}",
        "",
        "SECTION 3: MANDATORY WAITING PERIOD SCHEDULE",
        "-" * 80,
        f"Initial Waiting Period : {p['waiting_periods'].get('initial_days', 30)} Days (Waived for Accidental Injury)",
        f"Specific Disease Period: {p['waiting_periods'].get('specific_disease_months', 24)} Months",
        f"Pre-Existing Disease   : {p['waiting_periods'].get('ped_months', 36)} Months of Continuous Coverage",
        f"Statutory Moratorium   : {p['waiting_periods'].get('statutory_moratorium_months', 60)} Months",
        "",
        "SECTION 4: CO-PAYMENT & ANNUAL DEDUCTIBLE PROVISIONS",
        "-" * 80,
        f"Mandatory Co-Payment   : {p['co_payment'].get('mandatory_pct', '0.00')}%",
        f"Deductible Amount      : INR {p['deductible'].get('amount', '0.00')} ({p['deductible'].get('type', 'none')})",
        "",
        "SECTION 5: SPECIFIC PROCEDURE & DISEASE SUB-LIMIT SCHEDULE",
        "-" * 80,
    ]

    sublimits = p.get("disease_sublimits", {})
    if sublimits:
        for cond, details in sublimits.items():
            lines.append(f"  * {cond:<25} : INR {details['cap_inr']:<12} ({details.get('per', 'per admission')})")
    else:
        lines.append("  * No disease-specific sub-limits applicable. Up to Sum Insured.")

    lines.extend([
        "",
        "SECTION 6: PERMANENT & STATUTORY EXCLUSIONS",
        "-" * 80,
    ])
    for ex in p.get("exclusions", {}).get("permanent", []):
        lines.append(f"  [X] {ex}")

    lines.extend([
        "",
        "SECTION 7: NETWORK HOSPITALIZATION & PRE-AUTH GUIDELINES",
        "-" * 80,
        p.get("network_hospital_conditions", "Cashless empanelment only."),
        "Pre-Authorisation Mandate: Planned admissions require submission 48 hours prior;",
        "Emergency hospitalizations require intimation within 24 hours of admission.",
        "=" * 80,
    ])
    return "\n".join(lines)


def render_policy_pdf(p: dict[str, Any], out_path: Path):
    """Render policy schedule into a professional PDF using ReportLab."""
    doc = SimpleDocTemplate(str(out_path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1A365D"),
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4A5568"),
        alignment=1,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=8,
        spaceAfter=4,
    )
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8, leading=10)

    story = [
        Paragraph(f"<b>{p['insurer_name'].upper()}</b>", title_style),
        Paragraph(f"POLICY SCHEDULE: {p['policy_name']} (UIN: {p.get('product_uin', 'N/A')})", subtitle_style),
        Spacer(1, 10),
        Paragraph("1. Policy Schedule & Benefit Entitlements", h2_style),
    ]

    t1_data = [
        [Paragraph("<b>Policy ID</b>", cell_style), Paragraph(p["policy_id"], cell_style), Paragraph("<b>Plan Type</b>", cell_style), Paragraph(p["policy_type"].upper(), cell_style)],
        [Paragraph("<b>Sum Insured</b>", cell_style), Paragraph(f"INR {p['sum_insured']['amount']}", cell_style), Paragraph("<b>Available SI</b>", cell_style), Paragraph(f"INR {p['available_sum_insured']['amount']}", cell_style)],
        [Paragraph("<b>Start Date</b>", cell_style), Paragraph(p["policy_start_date"], cell_style), Paragraph("<b>Expiry Date</b>", cell_style), Paragraph(p["policy_expiry_date"], cell_style)],
        [Paragraph("<b>Co-Payment</b>", cell_style), Paragraph(f"{p['co_payment'].get('mandatory_pct', '0.00')}%", cell_style), Paragraph("<b>Deductible</b>", cell_style), Paragraph(f"INR {p['deductible'].get('amount', '0.00')}", cell_style)],
    ]
    t1 = Table(t1_data, colWidths=[110, 160, 110, 160])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t1)
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. Room Rent, Waiting Periods & Sub-Limits", h2_style))
    rr_cap = p['room_rent_limits'].get('daily_cap_inr') or 'No Daily Cap / Actuals'
    wp_init = f"{p['waiting_periods'].get('initial_days', 30)} Days"
    wp_ped = f"{p['waiting_periods'].get('ped_months', 36)} Months"
    wp_spec = f"{p['waiting_periods'].get('specific_disease_months', 24)} Months"

    t2_data = [
        [Paragraph("<b>Daily Room Rent Limit</b>", cell_style), Paragraph(f"INR {rr_cap}", cell_style), Paragraph("<b>Initial Waiting Period</b>", cell_style), Paragraph(wp_init, cell_style)],
        [Paragraph("<b>Proportional Deduction</b>", cell_style), Paragraph("Yes (Clause 3.1.A)" if p['room_rent_limits'].get('proportional_deduction_applies') else "No", cell_style), Paragraph("<b>PED Waiting Period</b>", cell_style), Paragraph(wp_ped, cell_style)],
        [Paragraph("<b>ICU Limit</b>", cell_style), Paragraph(f"INR {p['icu_limits'].get('daily_cap_inr') or 'Actuals'}", cell_style), Paragraph("<b>Specific Disease WP</b>", cell_style), Paragraph(wp_spec, cell_style)],
    ]
    t2 = Table(t2_data, colWidths=[110, 160, 110, 160])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EDF2F7")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    story.append(Paragraph("3. Specific Disease Sub-Limits", h2_style))
    sublimits = p.get("disease_sublimits", {})
    if sublimits:
        sub_rows = [[Paragraph("<b>Condition / Procedure</b>", cell_style), Paragraph("<b>Maximum Sub-Limit (INR)</b>", cell_style), Paragraph("<b>Clause Reference</b>", cell_style)]]
        for cond, d in sublimits.items():
            sub_rows.append([Paragraph(cond, cell_style), Paragraph(f"INR {d['cap_inr']}", cell_style), Paragraph(d.get("clause", "Schedule B"), cell_style)])
        t3 = Table(sub_rows, colWidths=[180, 160, 200])
        t3.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ("PADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t3)
    else:
        story.append(Paragraph("<i>No disease-specific sub-limits apply. Admissible up to available Sum Insured.</i>", cell_style))

    doc.build(story)


def render_policy_docx(p: dict[str, Any], out_path: Path):
    """Render policy schedule into Microsoft Word DOCX format."""
    doc = DocxDocument()
    title = doc.add_heading(p["insurer_name"].upper(), level=0)
    title.runs[0].font.color.rgb = RGBColor(26, 54, 93)

    subtitle = doc.add_paragraph(f"SCHEDULE OF INSURANCE: {p['policy_name']} (UIN: {p.get('product_uin', 'N/A')})")
    subtitle.runs[0].font.size = Pt(11)
    subtitle.runs[0].font.italic = True

    doc.add_heading("1. Policy Schedule & Contract Details", level=1)
    t = doc.add_table(rows=4, cols=2)
    t.style = "Table Grid"
    rows = [
        ("Policy Identifier", p["policy_id"]),
        ("Plan Type", p["policy_type"].upper()),
        ("Sum Insured (INR)", f"₹ {p['sum_insured']['amount']}"),
        ("Coverage Period", f"{p['policy_start_date']} to {p['policy_expiry_date']}"),
    ]
    for i, (k, v) in enumerate(rows):
        t.cell(i, 0).text = k
        t.cell(i, 1).text = str(v)

    doc.add_heading("2. Waiting Periods & Exclusions", level=1)
    wp = p.get("waiting_periods", {})
    doc.add_paragraph(f"• Initial Waiting Period: {wp.get('initial_days', 30)} days")
    doc.add_paragraph(f"• Pre-Existing Disease (PED) Waiting Period: {wp.get('ped_months', 36)} months")
    doc.add_paragraph(f"• Specific Disease Waiting Period: {wp.get('specific_disease_months', 24)} months")

    doc.save(str(out_path))


def render_policy_image(p: dict[str, Any], out_path: Path, img_format: str = "PNG"):
    """Render policy schedule as a 1200x800 graphical certificate image."""
    img = Image.new("RGB", (1200, 800), color=(250, 252, 255))
    draw = ImageDraw.Draw(img)

    # Border
    draw.rectangle([20, 20, 1180, 780], outline=(43, 108, 176), width=3)
    draw.rectangle([26, 26, 1174, 774], outline=(203, 213, 224), width=1)

    # Title Banner
    draw.rectangle([30, 30, 1170, 110], fill=(26, 54, 93))
    draw.text((60, 45), p["insurer_name"].upper(), fill=(255, 255, 255))
    draw.text((60, 75), f"POLICY CERTIFICATE: {p['policy_name']} (ID: {p['policy_id']})", fill=(226, 232, 240))

    # Details
    draw.text((60, 140), "SECTION 1: CORE POLICY ENTITLEMENTS", fill=(43, 108, 176))
    draw.line([60, 160, 500, 160], fill=(43, 108, 176), width=2)
    draw.text((60, 180), f"Policy Number     : {p['policy_id']}", fill=(45, 55, 72))
    draw.text((60, 210), f"Plan Category     : {p['policy_type'].upper()}", fill=(45, 55, 72))
    draw.text((60, 240), f"Sum Insured       : INR {p['sum_insured']['amount']}", fill=(45, 55, 72))
    draw.text((60, 270), f"Policy Period     : {p['policy_start_date']} to {p['policy_expiry_date']}", fill=(45, 55, 72))
    draw.text((60, 300), f"Co-Payment        : {p['co_payment'].get('mandatory_pct', '0.00')}%", fill=(45, 55, 72))

    draw.text((600, 140), "SECTION 2: ROOM RENT & WAITING PERIODS", fill=(43, 108, 176))
    draw.line([600, 160, 1100, 160], fill=(43, 108, 176), width=2)
    rr_cap = p['room_rent_limits'].get('daily_cap_inr') or 'No Cap / Actuals'
    draw.text((600, 180), f"Room Rent Limit   : INR {rr_cap}", fill=(45, 55, 72))
    draw.text((600, 210), f"Initial Waiting   : {p['waiting_periods'].get('initial_days', 30)} Days", fill=(45, 55, 72))
    draw.text((600, 240), f"Specific Disease  : {p['waiting_periods'].get('specific_disease_months', 24)} Months", fill=(45, 55, 72))
    draw.text((600, 270), f"Pre-Existing (PED): {p['waiting_periods'].get('ped_months', 36)} Months", fill=(45, 55, 72))
    draw.text((600, 300), f"Moratorium Period : {p['waiting_periods'].get('statutory_moratorium_months', 60)} Months", fill=(45, 55, 72))

    # Sub-limits table
    draw.text((60, 360), "SECTION 3: SCHEDULED SUB-LIMITS", fill=(43, 108, 176))
    draw.line([60, 380, 1100, 380], fill=(43, 108, 176), width=2)
    y = 400
    sublimits = p.get("disease_sublimits", {})
    if sublimits:
        for cond, d in list(sublimits.items())[:6]:
            draw.text((60, y), f"• {cond:<30} : INR {d['cap_inr']}", fill=(45, 55, 72))
            y += 30
    else:
        draw.text((60, y), "No disease-specific sub-limits applicable. Full Sum Insured available.", fill=(74, 85, 104))

    # Footer
    draw.line([60, 720, 1140, 720], fill=(203, 213, 224), width=1)
    draw.text((60, 735), f"Issued by {p['insurer_name']} • IRDAI Registered Health Insurance Product", fill=(113, 128, 150))

    img.save(str(out_path), format=img_format)


def render_all_policies(base_dir: Path):
    """Render all 35 canonical policies into all 6 document formats."""
    canonical_dir = base_dir / "policies" / "canonical"
    p_files = sorted(canonical_dir.glob("POL-*.json"))

    json_dir = base_dir / "policies" / "json"
    txt_dir = base_dir / "policies" / "txt"
    pdf_dir = base_dir / "policies" / "pdf"
    docx_dir = base_dir / "policies" / "docx"
    png_dir = base_dir / "policies" / "png"
    jpg_dir = base_dir / "policies" / "jpg"

    for d in [json_dir, txt_dir, pdf_dir, docx_dir, png_dir, jpg_dir]:
        d.mkdir(parents=True, exist_ok=True)

    rendered_counts = {"json": 0, "txt": 0, "pdf": 0, "docx": 0, "png": 0, "jpg": 0}

    for pf in p_files:
        with open(pf, "r", encoding="utf-8") as f:
            p = json.load(f)
        pid = p["policy_id"]

        # 1. JSON
        with open(json_dir / f"{pid}.json", "w", encoding="utf-8") as f:
            json.dump(p, f, indent=2)
        rendered_counts["json"] += 1

        # 2. TXT
        txt_content = format_policy_as_text(p)
        with open(txt_dir / f"{pid}.txt", "w", encoding="utf-8") as f:
            f.write(txt_content)
        rendered_counts["txt"] += 1

        # 3. PDF
        render_policy_pdf(p, pdf_dir / f"{pid}.pdf")
        rendered_counts["pdf"] += 1

        # 4. DOCX
        render_policy_docx(p, docx_dir / f"{pid}.docx")
        rendered_counts["docx"] += 1

        # 5. PNG
        render_policy_image(p, png_dir / f"{pid}.png", img_format="PNG")
        rendered_counts["png"] += 1

        # 6. JPG
        render_policy_image(p, jpg_dir / f"{pid}.jpg", img_format="JPEG")
        rendered_counts["jpg"] += 1

    print("\n--- POLICY DOCUMENT RENDERING COMPLETE ---")
    for fmt, count in rendered_counts.items():
        print(f"  {fmt.upper():<6}: {count} files generated")
    print(f"Total Policy Document Artifacts: {sum(rendered_counts.values())}")


def main():
    base_dir = PROJECT_ROOT / "synthetic_evaluation"
    render_all_policies(base_dir)


if __name__ == "__main__":
    main()
