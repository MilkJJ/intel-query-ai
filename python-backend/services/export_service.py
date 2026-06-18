from io import BytesIO
from typing import Any

from pptx import Presentation
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from schemas import ExportRequest


def _metadata_value(payload: ExportRequest, key: str, default: Any = None) -> Any:
    if key in payload.metadata:
        return payload.metadata.get(key, default)
    return getattr(payload, key, default)


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(value).strip()] if str(value).strip() else []


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

    transcript_summary = _metadata_value(payload, "transcript_summary", payload.transcription)
    detected_objects = _as_string_list(_metadata_value(payload, "detected_objects", payload.detected_objects))
    frame_text = _as_string_list(_metadata_value(payload, "frame_text", payload.frame_text))
    vision_summary = _metadata_value(payload, "vision_summary", {}) or {}

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

    sections = [
        ("Query", payload.query),
        ("Transcript Summary", transcript_summary or "No transcript summary available."),
        (
            "Detected Objects",
            ", ".join(detected_objects) if detected_objects else "No objects detected.",
        ),
        (
            "Extracted Frame Text",
            "\n".join(frame_text) if frame_text else "No frame text extracted.",
        ),
        (
            "Vision Insights",
            str(vision_summary) if vision_summary else "No vision insights available.",
        ),
        ("Agent response", payload.response),
    ]

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

    transcript_summary = _metadata_value(payload, "transcript_summary", payload.transcription)
    detected_objects = _as_string_list(_metadata_value(payload, "detected_objects", payload.detected_objects))
    frame_text = _as_string_list(_metadata_value(payload, "frame_text", payload.frame_text))
    vision_summary = _metadata_value(payload, "vision_summary", {}) or {}

    cover_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    cover_slide.shapes.title.text = payload.title
    cover_slide.placeholders[1].text = (
        f"Video: {payload.filename or 'Unknown'}\n"
        f"Agent: {payload.agent}\n"
        f"Language: {payload.language}\n"
        f"Duration: {payload.duration}"
    )

    add_ppt_body_slide(presentation, "Query", payload.query)
    add_ppt_body_slide(presentation, "Key Points", transcript_summary or "No transcript summary available.")
    add_ppt_body_slide(
        presentation,
        "Findings",
        "\n".join(
            [
                "Objects: " + (", ".join(detected_objects) if detected_objects else "none"),
                "Frame text: " + (" | ".join(frame_text[:5]) if frame_text else "none"),
                "Vision insights: " + (str(vision_summary) if vision_summary else "none"),
            ]
        ),
    )
    add_ppt_body_slide(
        presentation,
        "Conclusion",
        payload.response,
    )

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