"""
scripts/generate_pdf.py
-----------------------
Compiles PROJECT_CONTEXT.md into a professional, styled academic PDF document
using ReportLab Platypus.
"""

import re
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Preformatted
)
from reportlab.pdfgen import canvas

PROJECT_ROOT = Path("/Users/arunkumardhanasekaran/VS_code/LLM_Project")
MD_PATH = PROJECT_ROOT / "PROJECT_CONTEXT.md"
PDF_PATH = PROJECT_ROOT / "PROJECT_CONTEXT.pdf"


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw total page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "A1 Cashless Pre-Authorisation Agent — Project Context Document")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 742, letter[0] - 54, 742)

        # Footer
        text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 36, text)
        self.drawString(54, 36, "CONFIDENTIAL & PROPRIETARY — ACADEMIC KNOWLEDGE TRANSFER")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 48, letter[0] - 54, 48)
        
        self.restoreState()


def clean_markdown_inline(text: str) -> str:
    """Escapes XML entities and converts markdown inline tags to ReportLab tags."""
    # XML escape
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    
    # Bold **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Italic *text*
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)\*', r'<i>\1</i>', text)
    # Inline code `code`
    text = re.sub(r'`(.*?)`', r'<font face="Courier" color="#1E293B"><b>\1</b></font>', text)
    
    return text


def build_pdf():
    print("[*] Reading markdown content...")
    with open(MD_PATH, "r", encoding="utf-8") as f:
        md_text = f.read()

    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2563EB'),
        spaceAfter=15,
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#334155'),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )

    h3_style = ParagraphStyle(
        'H3',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#475569'),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=body_style,
        leftIndent=15,
        spaceAfter=3,
    )

    quote_style = ParagraphStyle(
        'Quote',
        parent=body_style,
        fontName='Helvetica-Oblique',
        textColor=colors.HexColor('#475569'),
        leftIndent=15,
        rightIndent=15,
        spaceAfter=8,
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#1E293B'),
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=table_cell_style,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#FFFFFF'),
    )

    code_style = ParagraphStyle(
        'CodeBlock',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#0F172A'),
    )

    story = []

    lines = md_text.split("\n")
    i = 0
    total_lines = len(lines)

    in_code_block = False
    code_block_lines = []

    in_table = False
    table_rows = []

    while i < total_lines:
        line = lines[i]

        # Handle Code Blocks
        if line.strip().startswith("```"):
            if in_code_block:
                # End of code block
                in_code_block = False
                code_text = "\n".join(code_block_lines)
                clean_code = clean_markdown_inline(code_text)
                
                # Split code into chunks of max 35 lines so it can split across pages smoothly
                code_chunk_size = 35
                for c_start in range(0, max(1, len(code_block_lines)), code_chunk_size):
                    chunk_text = "\n".join(code_block_lines[c_start:c_start + code_chunk_size])
                    code_p = Preformatted(chunk_text, code_style)
                    story.append(code_p)
                story.append(Spacer(1, 6))
                code_block_lines = []
            else:
                in_code_block = True
                code_block_lines = []
            i += 1
            continue

        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue

        # Handle Markdown Tables
        if "|" in line and (line.strip().startswith("|") or line.strip().endswith("|")):
            # Check if it's separator row
            if re.match(r'^\s*\|?\s*[-:]+[-| :]*\|?\s*$', line):
                i += 1
                continue
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            if cells:
                table_rows.append(cells)
                in_table = True
            i += 1
            continue
        elif in_table:
            # End of table
            in_table = False
            if table_rows:
                num_cols = len(table_rows[0])
                col_w = 504.0 / num_cols
                
                formatted_data = []
                for row_idx, row in enumerate(table_rows):
                    row_cells = []
                    for c_idx in range(num_cols):
                        val = row[c_idx] if c_idx < len(row) else ""
                        c_text = clean_markdown_inline(val)
                        if row_idx == 0:
                            p = Paragraph(c_text, table_header_style)
                        else:
                            p = Paragraph(c_text, table_cell_style)
                        row_cells.append(p)
                    formatted_data.append(row_cells)

                t = Table(formatted_data, colWidths=[col_w] * num_cols)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ]))
                story.append(t)
                story.append(Spacer(1, 8))
                table_rows = []

        # Empty line
        if not line.strip():
            story.append(Spacer(1, 4))
            i += 1
            continue

        # Horizontal Rule
        if line.strip() in ("---", "***", "___"):
            story.append(Spacer(1, 6))
            i += 1
            continue

        # Document Title (# PROJECT_CONTEXT.md)
        if line.startswith("# "):
            clean_text = clean_markdown_inline(line[2:].strip())
            story.append(Paragraph(clean_text, title_style))
            i += 1
            continue

        # Section Heading (## Section X: ...)
        if line.startswith("## "):
            clean_text = clean_markdown_inline(line[3:].strip())
            story.append(Spacer(1, 8))
            story.append(Paragraph(clean_text, h1_style))
            i += 1
            continue

        # Subheading (### X.Y ...)
        if line.startswith("### "):
            clean_text = clean_markdown_inline(line[4:].strip())
            story.append(Paragraph(clean_text, h2_style))
            i += 1
            continue

        # Sub-subheading (#### X.Y.Z ...)
        if line.startswith("#### "):
            clean_text = clean_markdown_inline(line[5:].strip())
            story.append(Paragraph(clean_text, h3_style))
            i += 1
            continue

        # Blockquote (> ...)
        if line.startswith("> "):
            clean_text = clean_markdown_inline(line[2:].strip())
            story.append(Paragraph(clean_text, quote_style))
            i += 1
            continue

        # Bullet point (- or * )
        if re.match(r'^\s*[-*]\s+', line):
            clean_text = clean_markdown_inline(re.sub(r'^\s*[-*]\s+', '', line))
            bullet_html = f"&bull; {clean_text}"
            story.append(Paragraph(bullet_html, bullet_style))
            i += 1
            continue

        # Numbered list
        if re.match(r'^\s*\d+\.\s+', line):
            num = re.match(r'^\s*(\d+)\.\s+', line).group(1)
            clean_text = clean_markdown_inline(re.sub(r'^\s*\d+\.\s+', '', line))
            num_html = f"<b>{num}.</b> {clean_text}"
            story.append(Paragraph(num_html, bullet_style))
            i += 1
            continue

        # Regular paragraph
        clean_text = clean_markdown_inline(line.strip())
        if clean_text:
            story.append(Paragraph(clean_text, body_style))
        i += 1

    print(f"[*] Building PDF with {len(story)} flowable elements...")
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[+] Successfully generated {PDF_PATH}")


if __name__ == "__main__":
    build_pdf()
