"""
ReportAgent — generates PDF and PowerPoint reports from video analysis results.

Workflow:
  1. If no transcript is cached in context, delegates to TranscriptionAgent
     to populate it first.
  2. Signals to the caller that /export should be called with the appropriate
     format to receive the actual file download.

The actual PDF/PPTX generation happens in services/export_service.py.
The /export endpoint in main.py handles the file streaming.

MCP integration note:
  In a future MCP setup, generate_pdf and generate_ppt can be registered as
  tools that accept a session_id, look up cached context, and return a
  download URL or base64-encoded file.
"""

import logging
from pathlib import Path

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.result import AgentResult


logger = logging.getLogger(__name__)


class ReportAgent(BaseAgent):
    name = "report"

    def __init__(self, transcription_agent):
        self._transcription_agent = transcription_agent

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

    # ── Shared helper ─────────────────────────────────────────────────────────

    def _ensure_transcript(self, context: AgentContext) -> str:
        """
        Return the cached transcript from context, transcribing the video first
        if the transcript is not yet available.
        """
        if not context.transcript:
            logger.info("ReportAgent: no cached transcript, requesting transcription...")
            saved_action = context.action
            context.action = "get_transcript"
            tx_result = self._transcription_agent.run(context)
            context.transcript = tx_result.transcription
            context.action = saved_action
        return context.transcript

    # ── Actions (MCP tools) ───────────────────────────────────────────────────

    def generate_pdf(self, context: AgentContext) -> AgentResult:
        """
        Prepare context for PDF export and instruct the caller to use /export.
        The transcript is guaranteed to be populated in context after this call.
        """
        transcript = self._ensure_transcript(context)
        video_name = Path(context.video_path).name

        return AgentResult(
            agent=self.name,
            action="generate_pdf",
            response=(
                f"PDF report is ready to download for '{video_name}'. "
                "Use the export button or call POST /export with format='pdf' to receive the file."
            ),
            transcription=transcript,
            note="POST /export  { format: 'pdf', ... }  to download the PDF report.",
        )

    def generate_ppt(self, context: AgentContext) -> AgentResult:
        """
        Prepare context for PowerPoint export and instruct the caller to use /export.
        The transcript is guaranteed to be populated in context after this call.
        """
        transcript = self._ensure_transcript(context)
        video_name = Path(context.video_path).name

        return AgentResult(
            agent=self.name,
            action="generate_ppt",
            response=(
                f"PowerPoint presentation is ready to download for '{video_name}'. "
                "Use the export button or call POST /export with format='ppt' to receive the file."
            ),
            transcription=transcript,
            note="POST /export  { format: 'ppt', ... }  to download the PPTX presentation.",
        )
