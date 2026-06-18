import logging
import os

from fastapi import HTTPException

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.result import AgentResult
from services.media_service import extract_audio
from services.transcription_service import transcribe_audio


logger = logging.getLogger(__name__)


class TranscriptionAgent(BaseAgent):
    name = "transcription"

    @property
    def actions(self):
        return {
            "get_transcript": self.get_transcript,
            "summarize_transcript": self.summarize_transcript,
            "answer_query": self.answer_query,
        }

    def run(self, context: AgentContext) -> AgentResult:
        action = context.action or "get_transcript"
        handler = self.actions.get(action)
        if handler is None:
            raise ValueError(f"TranscriptionAgent: unknown action '{action}'")
        return handler(context)

    # ── Shared helper ─────────────────────────────────────────────────────────

    def _extract_and_transcribe(self, context: AgentContext) -> dict:
        """Extract audio from video, transcribe it, and clean up the audio file."""
        audio_path = f"{context.video_path}.wav"
        if not extract_audio(context.video_path, audio_path):
            raise HTTPException(
                status_code=500,
                detail="Failed to extract audio from video. Check if FFmpeg is installed.",
            )
        try:
            result = transcribe_audio(audio_path)
            context.transcript = result["transcription"]  # cache for downstream agents
            return result
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info("✓ Cleaned up audio file")

    # ── Actions (MCP tools) ───────────────────────────────────────────────────

    def get_transcript(self, context: AgentContext) -> AgentResult:
        """Return the full verbatim transcript of the video."""
        result = self._extract_and_transcribe(context)
        transcript_text = result["transcription"]
        return AgentResult(
            agent=self.name,
            action="get_transcript",
            response=transcript_text or "No speech detected in the video.",
            transcription=transcript_text,
            language=result.get("language", "unknown"),
            duration=result.get("duration", 0.0),
        )

    def summarize_transcript(self, context: AgentContext) -> AgentResult:
        """Return a concise summary of the spoken content."""
        result = self._extract_and_transcribe(context)
        transcript_text = result["transcription"]

        if not transcript_text:
            summary = "No spoken content was detected to summarize."
        else:
            sentences = [s.strip() for s in transcript_text.replace(". ", ".\n").split("\n") if s.strip()]
            summary = "Summary: " + " ".join(sentences[:5])

        return AgentResult(
            agent=self.name,
            action="summarize_transcript",
            response=summary,
            transcription=transcript_text,
            language=result.get("language", "unknown"),
            duration=result.get("duration", 0.0),
        )

    def answer_query(self, context: AgentContext) -> AgentResult:
        """Use the transcript as context to answer an open-ended query."""
        result = self._extract_and_transcribe(context)
        transcript_text = result["transcription"]

        if not transcript_text:
            response = "No spoken content detected in the video. Cannot answer the query."
        else:
            response = (
                f"Based on the video transcript:\n\n{transcript_text[:1500]}"
                + ("\n\n[transcript truncated]" if len(transcript_text) > 1500 else "")
            )

        return AgentResult(
            agent=self.name,
            action="answer_query",
            response=response,
            transcription=transcript_text,
            language=result.get("language", "unknown"),
            duration=result.get("duration", 0.0),
        )