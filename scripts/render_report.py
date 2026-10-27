"""Render the project Markdown report as a readable, paginated PDF.

Requires reportlab; use the bundled document-runtime Python or install reportlab
in a separate document environment. It does not alter the experiment environment.
"""
import argparse
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted, Image


def inline(text):
    text = text.replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', ' - ')
    text = escape(text)
    text = re.sub(r'`([^`]+)`', r'<font name="Courier" size="8">\1</font>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', text)
    text = re.sub(r'(https?://[^\s<>]+)', r'<link href="\1" color="#17618a">\1</link>', text)
    return text


def render(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    body = ParagraphStyle('ReportBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10,
                          leading=14, spaceAfter=7, textColor=colors.HexColor('#24313d'),
                          splitLongWords=True, allowWidows=0, allowOrphans=0)
    title = ParagraphStyle('ReportTitle', parent=body, fontName='Helvetica-Bold', fontSize=23,
                           leading=28, textColor=colors.HexColor('#16354b'), spaceAfter=15)
    heading = ParagraphStyle('ReportHeading', parent=body, fontName='Helvetica-Bold', fontSize=14,
                             leading=18, spaceBefore=14, spaceAfter=8, keepWithNext=True)
    subheading = ParagraphStyle('ReportSubheading', parent=heading, fontSize=11, leading=15,
                                spaceBefore=9, spaceAfter=6)
    cell = ParagraphStyle('Cell', parent=body, fontSize=8, leading=10.5, spaceAfter=0)
    numeric_cell = ParagraphStyle('NumericCell', parent=cell, alignment=TA_RIGHT)
    header_cell = ParagraphStyle('HeaderCell', parent=cell, fontName='Helvetica-Bold', textColor=colors.white)
    bullet = ParagraphStyle('Bullet', parent=body, leftIndent=12, firstLineIndent=-8)
    code = ParagraphStyle('Code', fontName='Courier', fontSize=7, leading=9, spaceAfter=8)
    width = A4[0]-88
    story, buffer, table_lines = [], [], []

    def flush_text():
        if buffer:
            story.append(Paragraph(inline(' '.join(buffer)), body))
            buffer.clear()

    def flush_table():
        if not table_lines:
            return
        rows = [[part.strip() for part in line.strip().strip('|').split('|')] for line in table_lines]
        rows = [row for row in rows if not all(re.fullmatch(r':?-+:?', part.replace(' ', '')) for part in row)]
        columns = len(rows[0])
        if any(len(row) != columns for row in rows):
            raise ValueError('Inconsistent Markdown table column count')
        if columns == 2:
            widths = [width*.31, width*.69]
        elif columns == 3:
            widths = [width*.18, width*.33, width*.49]
        else:
            widths = [width/columns]*columns
        data = [[Paragraph(inline(part), header_cell if i == 0 else
                           numeric_cell if re.fullmatch(r'[+\-\d.,% /]+', part) else cell) for part in row]
                for i, row in enumerate(rows)]
        table = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16354b')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f2f6f8'), colors.white]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, -1), (-1, -1), .4, colors.HexColor('#cbd5dd'))]))
        story.extend([table, Spacer(1, 9)])
        table_lines.clear()

    in_code, code_lines = False, []
    for line in source.read_text(encoding='utf-8').splitlines():
        if line.startswith('```'):
            flush_text(); flush_table()
            if in_code:
                story.append(Preformatted('\n'.join(code_lines), code, maxLineLength=100))
                code_lines.clear()
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue
        if line.lstrip().startswith('|'):
            flush_text(); table_lines.append(line)
            continue
        flush_table()
        image_match = re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)', line.strip())
        if image_match:
            flush_text()
            asset = (source.parent/image_match.group(2)).resolve()
            picture = Image(str(asset))
            ratio = min(width/picture.imageWidth, 310/picture.imageHeight)
            picture.drawWidth, picture.drawHeight = picture.imageWidth*ratio, picture.imageHeight*ratio
            picture.hAlign = 'LEFT'
            story.extend([picture, Paragraph(inline(image_match.group(1)), cell), Spacer(1, 9)])
        elif not line.strip():
            flush_text()
        elif line.startswith('# '):
            flush_text(); story.append(Paragraph(inline(line[2:]), title))
        elif line.startswith('## '):
            flush_text(); story.append(Paragraph(inline(line[3:]), heading))
        elif line.startswith('### '):
            flush_text(); story.append(Paragraph(inline(line[4:]), subheading))
        elif line.startswith('- '):
            flush_text(); story.append(Paragraph('- '+inline(line[2:]), bullet))
        elif re.match(r'^\d+\. ', line):
            flush_text(); story.append(Paragraph(inline(line), body))
        else:
            buffer.append(line.strip())
    flush_text(); flush_table()

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#697987'))
        canvas.drawString(44, A4[1]-28, 'PE6203  |  Tool Harness Adaptation')
        canvas.drawRightString(A4[0]-44, 25, str(doc.page))
        canvas.drawString(44, 25, 'Local-model experiment | Reproducible evidence accompanies the report')
        canvas.restoreState()

    doc = SimpleDocTemplate(str(destination), pagesize=A4, leftMargin=44, rightMargin=44,
                            topMargin=47, bottomMargin=45, title='PE6203 Project 4: Tool Harness Adaptation',
                            author='PE6203 project team - AI-assisted preparation')
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    print(destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    render(args.source.resolve(), args.destination.resolve())
