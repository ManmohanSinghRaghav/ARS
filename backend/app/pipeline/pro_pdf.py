from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import io

def generate_pro_pdf(paper_json: dict) -> bytes:
    """Generates a high-fidelity PDF from structured paper JSON using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=22,
        alignment=TA_CENTER,
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor='#555555'
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitleStyle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        fontName='Helvetica-Bold',
        textTransform='uppercase'
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=10
    )
    
    abstract_box_style = ParagraphStyle(
        'AbstractStyle',
        parent=body_style,
        fontSize=10,
        leftIndent=20,
        rightIndent=20,
        backColor='#F9F9F9',
        borderPadding=10,
        italic=True
    )

    elements = []
    
    # Metadata
    metadata = paper_json.get("metadata", {})
    elements.append(Paragraph(metadata.get("title", "Untitled Research"), title_style))
    
    meta_line = f"{metadata.get('author', 'ARS')}<br/>{metadata.get('institution', 'GLA Research Lab')} • {metadata.get('date', '2026')}"
    elements.append(Paragraph(meta_line, meta_style))
    
    elements.append(Spacer(1, 20))
    
    # Sections
    sections = paper_json.get("sections", [])
    for section in sections:
        s_type = section.get("type", "content")
        s_title = section.get("title", "")
        s_content = section.get("content", "")
        
        if s_type == "abstract":
            elements.append(Paragraph("Abstract", section_title_style))
            elements.append(Paragraph(s_content, abstract_box_style))
        else:
            if s_title:
                elements.append(Paragraph(s_title, section_title_style))
            # Clean content for ReportLab (simple <br/> replacement for newlines)
            clean_content = s_content.replace('\n', '<br/>')
            elements.append(Paragraph(clean_content, body_style))
            
    doc.build(elements)
    return buffer.getvalue()
