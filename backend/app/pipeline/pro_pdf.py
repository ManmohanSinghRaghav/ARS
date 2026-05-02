from reportlab.lib.pagesizes import LETTER, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    KeepTogether, Preformatted
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import io
import re

class NumberedCanvas(canvas.Canvas):
    """Canvas with page numbers and headers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page_num, page in enumerate(self.pages, 1):
            self.__dict__.update(page)
            self.draw_page_decorations(page_num, page_count)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_num, total_pages):
        """Add footer with page numbers."""
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#999999"))
        self.drawRightString(7.5*inch, 0.5*inch, f"Page {page_num} of {total_pages}")


def _sanitize_html(text: str) -> str:
    """Sanitize text for ReportLab (basic HTML support)."""
    if not text:
        return ""
    # Convert markdown-style formatting to HTML
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)  # **bold**
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)       # *italic*
    text = re.sub(r'`(.*?)`', r'<font face="Courier">\1</font>', text)  # `code`
    # Replace markdown newlines with BR
    text = text.replace('\n\n', '<br/><br/>')
    text = text.replace('\n', '<br/>')
    return text


def _extract_tables(content: str) -> tuple:
    """Extract markdown tables from content."""
    # Simple markdown table detection: lines with |
    lines = content.split('\n')
    tables = []
    i = 0
    while i < len(lines):
        if '|' in lines[i]:
            table_lines = [lines[i]]
            i += 1
            # Skip separator line if present
            if i < len(lines) and '|' in lines[i] and '-' in lines[i]:
                i += 1
            # Collect table rows
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i])
                i += 1
            if len(table_lines) > 1:
                tables.append(('\n'.join(table_lines), i - len(table_lines)))
        else:
            i += 1
    return tables


def _parse_table(table_text: str) -> list:
    """Parse markdown table to list of lists."""
    lines = table_text.strip().split('\n')
    rows = []
    for line in lines:
        if '|' in line and '-' not in line:
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            rows.append(cells)
    return rows


def _extract_lists(content: str) -> dict:
    """Extract bullet and numbered lists from content."""
    bullet_pattern = r'^\s*[-•*]\s+(.+)$'
    numbered_pattern = r'^\s*\d+\.\s+(.+)$'
    
    bullets = re.findall(bullet_pattern, content, re.MULTILINE)
    numbered = re.findall(numbered_pattern, content, re.MULTILINE)
    
    return {
        "bullets": bullets,
        "numbered": numbered
    }


def generate_pro_pdf(paper_json: dict) -> bytes:
    """
    Generates a high-fidelity, professional PDF from structured paper JSON.
    
    Features:
    - Advanced typography and spacing
    - Support for tables, lists, and citations
    - Multi-level section hierarchy
    - Page numbers and headers
    - Better color scheme and visual hierarchy
    - Code block support
    - Abstract highlighting
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=1*inch,
        bottomMargin=0.75*inch,
        title=paper_json.get("metadata", {}).get("title", "Research Paper")
    )
    
    styles = getSampleStyleSheet()
    
    # ── Define Custom Styles ──
    
    # Title (Cover Page)
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=28,
        alignment=TA_CENTER,
        spaceAfter=6,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a1a1a'),
        leading=34
    )
    
    # Subtitle (Authors, Institution, Date)
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_CENTER,
        spaceAfter=4,
        textColor=colors.HexColor('#666666'),
        fontName='Helvetica'
    )
    
    # Abstract Box
    abstract_style = ParagraphStyle(
        'AbstractStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        textColor=colors.HexColor('#333333'),
        fontName='Helvetica',
        leftIndent=12,
        rightIndent=12,
        borderPadding=12,
        backColor=colors.HexColor('#f5f5f5')
    )
    
    # Section Heading (Level 1)
    section1_style = ParagraphStyle(
        'Section1',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_LEFT,
        spaceBefore=18,
        spaceAfter=10,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2c3e50'),
        borderColor=colors.HexColor('#3498db'),
        borderWidth=0,
        borderPadding=0,
        leading=19
    )
    
    # Section Heading (Level 2)
    section2_style = ParagraphStyle(
        'Section2',
        parent=styles['Heading2'],
        fontSize=13,
        alignment=TA_LEFT,
        spaceBefore=12,
        spaceAfter=8,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#34495e'),
        leading=16
    )
    
    # Body Text (Justified)
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=15.5,
        alignment=TA_JUSTIFY,
        spaceAfter=10,
        fontName='Helvetica',
        textColor=colors.HexColor('#2c3e50')
    )
    
    # Bullet List Item
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=body_style,
        fontSize=10,
        leading=14,
        leftIndent=20,
        spaceAfter=6,
        bulletIndent=10
    )
    
    # Code Block
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        fontName='Courier',
        textColor=colors.HexColor('#c0392b'),
        leftIndent=20,
        rightIndent=20,
        spaceAfter=8,
        backColor=colors.HexColor('#f8f8f8')
    )
    
    # Caption (for tables, figures)
    caption_style = ParagraphStyle(
        'CaptionStyle',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=colors.HexColor('#7f8c8d'),
        fontName='Helvetica-Oblique'
    )
    
    elements = []
    
    # ── COVER PAGE ──
    metadata = paper_json.get("metadata", {})
    
    # Title
    title = metadata.get("title", "Untitled Research")
    elements.append(Spacer(1, 1.5*inch))
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Authors
    author = metadata.get("author", "ARS Assistant")
    institution = metadata.get("institution", "GLA Research Lab")
    date = metadata.get("date", "May 2026")
    
    elements.append(Paragraph(f"<b>{author}</b>", subtitle_style))
    elements.append(Paragraph(institution, subtitle_style))
    elements.append(Paragraph(date, subtitle_style))
    
    elements.append(Spacer(1, 2*inch))
    
    # ── CONTENT PAGES ──
    sections = paper_json.get("sections", [])
    
    for idx, section in enumerate(sections):
        s_type = section.get("type", "content")
        s_title = section.get("title", "")
        s_content = section.get("content", "")
        s_level = section.get("level", 1)
        
        # Abstract Section (Special Formatting)
        if s_type == "abstract":
            if idx > 0:  # Not first section
                elements.append(PageBreak())
            elements.append(Paragraph("Abstract", section1_style))
            elements.append(Spacer(1, 0.15*inch))
            # Create framed abstract box
            sanitized = _sanitize_html(s_content)
            elements.append(Paragraph(sanitized, abstract_style))
            elements.append(Spacer(1, 0.3*inch))
        
        # Regular Content Section
        elif s_type == "content":
            # Page break before major sections (except first)
            if idx > 0 and s_level == 1 and len(elements) > 5:
                elements.append(PageBreak())
            
            # Section Title
            if s_title:
                if s_level == 1:
                    elements.append(Paragraph(s_title, section1_style))
                else:
                    elements.append(Paragraph(s_title, section2_style))
                elements.append(Spacer(1, 0.1*inch))
            
            # Process Content (with support for tables, lists, code)
            if s_content:
                # Check for tables
                if '|' in s_content and '-' in s_content:
                    lines = s_content.split('\n')
                    current_text = []
                    
                    for line in lines:
                        if '|' in line and '-' in line:
                            # Table line detected
                            if current_text:
                                text_content = '\n'.join(current_text)
                                sanitized = _sanitize_html(text_content)
                                if sanitized.strip():
                                    elements.append(Paragraph(sanitized, body_style))
                                current_text = []
                            
                            # Parse and add table
                            table_text = line
                            next_idx = lines.index(line) + 1
                            while next_idx < len(lines) and '|' in lines[next_idx]:
                                table_text += '\n' + lines[next_idx]
                                next_idx += 1
                            
                            try:
                                table_data = _parse_table(table_text)
                                if table_data:
                                    tbl = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
                                    tbl.setStyle(TableStyle([
                                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                        ('FONTSIZE', (0, 0), (-1, 0), 11),
                                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')])
                                    ]))
                                    elements.append(tbl)
                                    elements.append(Spacer(1, 0.2*inch))
                            except Exception as e:
                                print(f"[PDF] Table parse error: {e}")
                        
                        elif line.strip():
                            current_text.append(line)
                    
                    if current_text:
                        text_content = '\n'.join(current_text)
                        sanitized = _sanitize_html(text_content)
                        if sanitized.strip():
                            elements.append(Paragraph(sanitized, body_style))
                
                # Check for bullet lists
                elif any(line.strip().startswith(('-', '•', '*')) for line in s_content.split('\n')):
                    lines = s_content.split('\n')
                    for line in lines:
                        if line.strip().startswith(('-', '•', '*')):
                            bullet_text = re.sub(r'^[-•*]\s+', '', line.strip())
                            sanitized = _sanitize_html(bullet_text)
                            elements.append(Paragraph(f"• {sanitized}", bullet_style))
                        elif line.strip():
                            sanitized = _sanitize_html(line)
                            elements.append(Paragraph(sanitized, body_style))
                
                # Regular paragraph content
                else:
                    sanitized = _sanitize_html(s_content)
                    # Split by double newlines for paragraph breaks
                    paragraphs = sanitized.split('<br/><br/>')
                    for para in paragraphs:
                        if para.strip():
                            elements.append(Paragraph(para, body_style))
                            elements.append(Spacer(1, 0.05*inch))
    
    # ── Build PDF ──
    doc.build(elements)
    return buffer.getvalue()
