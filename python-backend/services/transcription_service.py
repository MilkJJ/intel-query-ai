import logging

from fastapi import HTTPException
from faster_whisper import WhisperModel


logger = logging.getLogger(__name__)

whisper_model = None
try:
    logger.info("Loading Whisper model...")
    whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    logger.info("✓ Whisper model loaded successfully")
except Exception as error:
    logger.error(f"Failed to load Whisper model: {error}")


def transcribe_audio(audio_path: str) -> dict:
    if not whisper_model:
        raise HTTPException(status_code=500, detail="Whisper model not initialized")

    try:
        logger.info(f"Transcribing audio from {audio_path}...")

        segments, info = whisper_model.transcribe(audio_path, beam_size=5)
        transcription = ""
        for segment in segments:
            transcription += segment.text + " "

        result = {
            "transcription": transcription.strip(),
            "language": info.language if hasattr(info, "language") else "unknown",
            "duration": info.duration if hasattr(info, "duration") else 0,
        }

        logger.info(f"✓ Transcription completed. Length: {len(result['transcription'])} characters")
        return result
    except Exception as error:
        logger.error(f"Transcription error: {error}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(error)}")