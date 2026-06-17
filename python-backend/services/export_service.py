from io import BytesIO

from pptx import Presentation
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from schemas import ExportRequest


def write_wrapped_pdf_text(pdf: canvas.Canvas, text: str, x: int, y: int, max_width: int, line_height: int) -> int:
    for paragraph in text.split("\n"):
        words = paragraph.split()

        if not words:
            y -= line_height
            continue

        current_line = words[0]
        for word in words[1:]:
            candidate_line = f"{current_line} {word}"
            if pdf.stringWidth(candidate_line, "Helvetica", 11) <= max_width:
                current_line = candidate_line
            else:
                pdf.drawString(x, y, current_line)
                y -= line_height
                current_line = word

        pdf.drawString(x, y, current_line)
        y -= line_height

    return y


def generate_pdf_report(payload: ExportRequest) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4
    y_position = page_height - 60

    pdf.setTitle(payload.title)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, y_position, payload.title)
    y_position -= 30

    pdf.setFont("Helvetica", 11)
    metadata_lines = [
        f"Source video: {payload.filename or 'Unknown'}",
        f"Agent: {payload.agent}",
        f"Language: {payload.language}",
        f"Duration: {payload.duration}",
    ]

    for line in metadata_lines:
        pdf.drawString(50, y_position, line)
        y_position -= 18

    sections = [("Query", payload.query), ("Agent response", payload.response)]
    if payload.transcription:
        sections.append(("Transcript", payload.transcription))

    for heading, content in sections:
        if y_position < 120:
            pdf.showPage()
            y_position = page_height - 60

        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(50, y_position, heading)
        y_position -= 20
        pdf.setFont("Helvetica", 11)
        y_position = write_wrapped_pdf_text(pdf, content, 50, y_position, int(page_width - 100), 16)
        y_position -= 10

    pdf.save()
    buffer.seek(0)
    return buffer


def add_ppt_body_slide(presentation: Presentation, title: str, body: str) -> None:
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = title
    text_frame = slide.placeholders[1].text_frame
    text_frame.clear()

    chunks = [chunk.strip() for chunk in body.split("\n") if chunk.strip()]
    if not chunks:
        chunks = ["No content available."]

    for index, chunk in enumerate(chunks):
        paragraph = text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
        paragraph.text = chunk


def generate_ppt_report(payload: ExportRequest) -> BytesIO:
    presentation = Presentation()

    cover_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    cover_slide.shapes.title.text = payload.title
    cover_slide.placeholders[1].text = (
        f"Video: {payload.filename or 'Unknown'}\n"
        f"Agent: {payload.agent}\n"
        f"Language: {payload.language}\n"
        f"Duration: {payload.duration}"
    )

    add_ppt_body_slide(presentation, "Query", payload.query)
    add_ppt_body_slide(presentation, "Agent response", payload.response)

    if payload.transcription:
        add_ppt_body_slide(presentation, "Transcript", payload.transcription[:3000])

    buffer = BytesIO()
    presentation.save(buffer)
    buffer.seek(0)
    return buffer


def generate_export_file(payload: ExportRequest) -> tuple[BytesIO, str, str]:
    export_format = payload.format.lower().strip()
    safe_stem = (payload.filename or payload.title or "video-ai-report").replace(" ", "-").lower()

    if export_format == "pdf":
        return generate_pdf_report(payload), "application/pdf", f"{safe_stem}.pdf"

    if export_format == "ppt":
        return (
            generate_ppt_report(payload),
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            f"{safe_stem}.pptx",
        )

    raise ValueError("Unsupported export format. Use 'pdf' or 'ppt'.")