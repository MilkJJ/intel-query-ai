"""
ReportAgent — generates local PDF and PowerPoint reports from analysis inputs.

Capabilities:
- Generate PDF summary from transcript summary, detected objects, and extracted frame text
- Generate PPT presentation with a title slide, key points slide, findings slide, and conclusion slide
- Return the saved file path plus structured metadata for downstream use

This agent is intentionally file-oriented so it can later be exposed via MCP
as a download-producing tool without changing the report generation logic.
"""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pptx import Presentation
from pptx.util import Inches, Pt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.result import AgentResult


logger = logging.getLogger(__name__)

DEFAULT_REPORT_TITLE = "Video AI Report"


class ReportAgent(BaseAgent):
    name = "report"

    def __init__(self, transcription_agent, vision_agent=None):
        self._transcription_agent = transcription_agent
        self._vision_agent = vision_agent

    @property
    def actions(self):
        return {
            "generate_pdf": self.generate_pdf,
            "generate_ppt": self.generate_ppt,
        }

    def run(self, context: AgentContext) -> AgentResult:
        action = context.action or "generate_pdf"
        handler = self.actions.get(action)
        if handler is None:
            raise ValueError(f"ReportAgent: unknown action '{action}'")
        return handler(context)

    # ── Input normalization ──────────────────────────────────────────────────

    def _ensure_transcript(self, context: AgentContext) -> str:
        if context.transcript:
            return context.transcript

        if self._transcription_agent is None:
            return ""

        saved_action = context.action
        try:
            context.action = "get_transcript"
            transcription_result = self._transcription_agent.run(context)
            context.transcript = transcription_result.transcription
            return context.transcript
        finally:
            context.action = saved_action

    def _ensure_transcript_summary(self, context: AgentContext) -> str:
        summary = context.metadata.get("transcript_summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()

        transcript = self._ensure_transcript(context)
        saved_action = context.action
        try:
            if self._transcription_agent is not None:
                context.action = "summarize_transcript"
                summary_result = self._transcription_agent.run(context)
                summary_text = summary_result.response.strip()
                if summary_text:
                    context.metadata["transcript_summary"] = summary_text
                    return summary_text
        except Exception:
            logger.warning("ReportAgent: transcript summarization failed, falling back to heuristic summary.")
        finally:
            context.action = saved_action

        heuristic_summary = self._summarize_transcript(transcript)
        context.metadata["transcript_summary"] = heuristic_summary
        return heuristic_summary

    def _summarize_transcript(self, transcript: str) -> str:
        if not transcript.strip():
            return "No transcript available."

        sentences = [sentence.strip() for sentence in transcript.replace("\n", " ").split(".") if sentence.strip()]
        summary_sentences = sentences[:5]
        if not summary_sentences:
            return transcript[:500]
        return ". ".join(summary_sentences) + ("." if not summary_sentences[-1].endswith(".") else "")

    def _coerce_string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, tuple):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str):
            return [value] if value.strip() else []
        return [str(value)]

    def _coerce_frame_text(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            frame_text: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("caption") or item.get("content")
                    if text and str(text).strip():
                        frame_text.append(str(text).strip())
                elif str(item).strip():
                    frame_text.append(str(item).strip())
            return frame_text
        if isinstance(value, dict):
            text = value.get("text") or value.get("caption") or value.get("content")
            return [str(text).strip()] if text and str(text).strip() else []
        if isinstance(value, str):
            return [value] if value.strip() else []
        return [str(value)] if str(value).strip() else []

    def _extract_vision_inputs(self, vision_result: AgentResult | None) -> tuple[list[str], list[str], dict[str, Any]]:
        if vision_result is None:
            return [], [], {}

        metadata = vision_result.metadata or {}
        summary = metadata.get("summary") if isinstance(metadata.get("summary"), dict) else {}
        if summary is None:
            summary = {}

        detected_objects = self._coerce_string_list(
            summary.get("objects_detected")
            or metadata.get("objects")
            or metadata.get("detected_objects")
            or vision_result.objects
        )

        frame_text = self._coerce_frame_text(
            summary.get("text_snippets")
            or metadata.get("frame_text")
            or metadata.get("text_frames")
            or metadata.get("frames")
        )

        return detected_objects, frame_text, metadata

    def _ensure_vision_analysis(self, context: AgentContext) -> AgentResult | None:
        if self._vision_agent is None:
            return None

        cached = context.metadata.get("vision_analysis")
        if isinstance(cached, dict):
            return None

        saved_action = context.action
        try:
            context.action = "analyze_video"
            vision_result = self._vision_agent.run(context)
            context.metadata["vision_analysis"] = vision_result.metadata
            return vision_result
        except Exception as error:
            logger.warning("ReportAgent: vision analysis failed, continuing without it: %s", error)
            return None
        finally:
            context.action = saved_action

    def _collect_analysis_inputs(self, context: AgentContext) -> dict[str, Any]:
        transcript = self._ensure_transcript(context)
        transcript_summary = self._ensure_transcript_summary(context)

        vision_result = self._ensure_vision_analysis(context)
        detected_objects, frame_text, vision_metadata = self._extract_vision_inputs(vision_result)

        detected_objects = context.metadata.get("detected_objects") or detected_objects
        detected_objects = self._coerce_string_list(detected_objects)

        frame_text = context.metadata.get("frame_text") or frame_text
        frame_text = self._coerce_string_list(frame_text)

        vision_summary = vision_metadata.get("summary") if isinstance(vision_metadata.get("summary"), dict) else {}
        if vision_summary is None:
            vision_summary = {}

        return {
            "title": context.metadata.get("report_title") or DEFAULT_REPORT_TITLE,
            "video_name": Path(context.video_path).name if context.video_path else "Unknown",
            "query": context.query,
            "transcript": transcript,
            "transcript_summary": transcript_summary,
            "detected_objects": detected_objects,
            "frame_text": frame_text,
            "vision_summary": vision_summary,
            "vision_metadata": vision_metadata,
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }

    def _report_directory(self, context: AgentContext) -> Path:
        root = Path(tempfile.gettempdir()) / "intel-query-ai-reports"
        if context.session_id:
            root = root / context.session_id
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _safe_stem(self, context: AgentContext, suffix: str) -> str:
        base_name = Path(context.video_path).stem if context.video_path else "report"
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        return f"{base_name}-{suffix}-{timestamp}".lower().replace(" ", "-")

    # ── PDF generation ───────────────────────────────────────────────────────

    def _build_pdf_story(self, report_data: dict[str, Any], styles) -> list[Any]:
        story: list[Any] = []

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#111827"),
            spaceAfter=10,
        )
        heading_style = ParagraphStyle(
            "ReportHeading",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["BodyText"],
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#111827"),
        )

        story.append(Paragraph(report_data["title"], title_style))
        story.append(Paragraph(f"Video: {report_data['video_name']}", body_style))
        story.append(Paragraph(f"Created: {report_data['created_at']}", body_style))
        story.append(Spacer(1, 6 * mm))

        sections = [
            ("Transcript Summary", report_data["transcript_summary"]),
            (
                "Detected Objects",
                ", ".join(report_data["detected_objects"]) if report_data["detected_objects"] else "No objects detected.",
            ),
            (
                "Extracted Frame Text",
                "\n".join(report_data["frame_text"]) if report_data["frame_text"] else "No frame text extracted.",
            ),
            (
                "Vision Insights",
                json.dumps(report_data["vision_summary"], indent=2, ensure_ascii=False)
                if report_data.get("vision_summary")
                else "No vision insights available.",
            ),
        ]

        for heading, content in sections:
            story.append(Paragraph(heading, heading_style))
            story.append(Paragraph(content.replace("\n", "<br/>") or "No content available.", body_style))
            story.append(Spacer(1, 4 * mm))

        summary_rows = [
            ["Transcript length", str(len(report_data["transcript"]))],
            ["Objects detected", str(len(report_data["detected_objects"]))],
            ["Text snippets", str(len(report_data["frame_text"]))],
            ["Vision frames", str(len(report_data.get("vision_metadata", {}).get("frames", [])) if isinstance(report_data.get("vision_metadata"), dict) else 0)],
        ]
        summary_table = Table(summary_rows, colWidths=[70 * mm, 90 * mm])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(summary_table)
        return story

    def _write_pdf(self, report_data: dict[str, Any], output_path: Path) -> None:
        styles = getSampleStyleSheet()
        document = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=report_data["title"],
        )
        story = self._build_pdf_story(report_data, styles)
        document.build(story)

    # ── PPT generation ───────────────────────────────────────────────────────

    def _add_title_slide(self, presentation: Any, report_data: dict[str, Any]) -> None:
        slide = presentation.slides.add_slide(presentation.slide_layouts[0])
        slide.shapes.title.text = report_data["title"]
        subtitle = slide.placeholders[1].text_frame
        subtitle.clear()
        subtitle.text = (
            f"Video: {report_data['video_name']}\n"
            f"Created: {report_data['created_at']}\n"
            f"Query: {report_data['query']}"
        )

    def _add_bullet_slide(self, presentation: Any, title: str, bullets: list[str]) -> None:
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = title
        text_frame = slide.placeholders[1].text_frame
        text_frame.clear()

        if not bullets:
            bullets = ["No content available."]

        for index, bullet in enumerate(bullets):
            paragraph = text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
            paragraph.text = bullet
            paragraph.level = 0

    def _write_ppt(self, report_data: dict[str, Any], output_path: Path) -> None:
        presentation = Presentation()
        presentation.slide_width = Inches(13.333)
        presentation.slide_height = Inches(7.5)

        self._add_title_slide(presentation, report_data)
        self._add_bullet_slide(
            presentation,
            "Key Points",
            [
                report_data["transcript_summary"] if report_data["transcript_summary"] else "No transcript summary available.",
                "Objects detected: " + (", ".join(report_data["detected_objects"]) if report_data["detected_objects"] else "none"),
                "Frame text snippets: " + (" | ".join(report_data["frame_text"][:3]) if report_data["frame_text"] else "none"),
            ],
        )

        findings = []
        if report_data["detected_objects"]:
            findings.append("Objects: " + ", ".join(report_data["detected_objects"]))
        else:
            findings.append("No detected objects were provided.")

        if report_data["frame_text"]:
            findings.append("Frame text: " + " | ".join(report_data["frame_text"][:5]))
        else:
            findings.append("No extracted frame text was provided.")

        self._add_bullet_slide(presentation, "Findings", findings)
        self._add_bullet_slide(
            presentation,
            "Conclusion",
            [
                "This report consolidates transcript, object, and frame-text analysis into a shareable summary.",
                "Use the structured metadata for follow-up automation or MCP tool integration.",
            ],
        )

        presentation.save(str(output_path))

    # ── Public actions ───────────────────────────────────────────────────────

    def generate_pdf(self, context: AgentContext) -> AgentResult:
        report_data = self._collect_analysis_inputs(context)
        report_dir = self._report_directory(context)
        output_path = report_dir / f"{self._safe_stem(context, 'summary')}.pdf"

        try:
            self._write_pdf(report_data, output_path)
        except Exception as error:
            logger.error("Failed to generate PDF report: %s", error, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to generate PDF report: {error}") from error

        metadata = {
            "format": "pdf",
            "file_path": str(output_path),
            "title": report_data["title"],
            "video_name": report_data["video_name"],
            "created_at": report_data["created_at"],
            "section_counts": {
                "objects": len(report_data["detected_objects"]),
                "frame_text": len(report_data["frame_text"]),
            },
            "sources": {
                "transcript_summary": bool(report_data["transcript_summary"]),
                "detected_objects": bool(report_data["detected_objects"]),
                "frame_text": bool(report_data["frame_text"]),
            },
        }

        response_payload = {
            "message": "PDF report generated successfully.",
            "file_path": str(output_path),
            "metadata": metadata,
        }
        return AgentResult(
            agent=self.name,
            action="generate_pdf",
            response=json.dumps(response_payload, indent=2, ensure_ascii=False),
            confidence=1.0,
            metadata=metadata,
        )

    def generate_ppt(self, context: AgentContext) -> AgentResult:
        report_data = self._collect_analysis_inputs(context)
        report_dir = self._report_directory(context)
        output_path = report_dir / f"{self._safe_stem(context, 'presentation')}.pptx"

        try:
            self._write_ppt(report_data, output_path)
        except Exception as error:
            logger.error("Failed to generate PPT report: %s", error, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to generate PPT report: {error}") from error

        metadata = {
            "format": "ppt",
            "file_path": str(output_path),
            "title": report_data["title"],
            "video_name": report_data["video_name"],
            "created_at": report_data["created_at"],
            "slides": ["title", "key points", "findings", "conclusion"],
            "sources": {
                "transcript_summary": bool(report_data["transcript_summary"]),
                "detected_objects": bool(report_data["detected_objects"]),
                "frame_text": bool(report_data["frame_text"]),
            },
        }

        response_payload = {
            "message": "PowerPoint report generated successfully.",
            "file_path": str(output_path),
            "metadata": metadata,
        }
        return AgentResult(
            agent=self.name,
            action="generate_ppt",
            response=json.dumps(response_payload, indent=2, ensure_ascii=False),
            confidence=1.0,
            metadata=metadata,
        )
