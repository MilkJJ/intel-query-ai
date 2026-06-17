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

    def can_handle(self, query: str) -> bool:
        normalized_query = query.lower().strip()
        return any(keyword in normalized_query for keyword in ["transcribe", "transcript", "caption"])

    def run(self, context: AgentContext) -> AgentResult:
        video_path = context.video_path
        audio_path = f"{video_path}.wav"
        audio_extracted = extract_audio(video_path, audio_path)

        if not audio_extracted:
            raise HTTPException(
                status_code=500,
                detail="Failed to extract audio from video. Check if FFmpeg is installed.",
            )

        try:
            transcription_result = transcribe_audio(audio_path)
            transcript_text = transcription_result["transcription"]
            return AgentResult(
                agent=self.name,
                response=transcript_text or "No speech detected in the video.",
                transcription=transcript_text,
                language=transcription_result.get("language", "unknown"),
                duration=transcription_result.get("duration", 0),
            )
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info("✓ Cleaned up audio file")