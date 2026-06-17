import logging
import subprocess


logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_FORMATS = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"}


def extract_audio(video_path: str, audio_path: str) -> bool:
    try:
        logger.info(f"Extracting audio from {video_path}...")

        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-y",
            audio_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False

        logger.info(f"✓ Audio extracted successfully to {audio_path}")
        return True
    except FileNotFoundError:
        logger.error("FFmpeg not found. Install it with: pip install ffmpeg-python OR install ffmpeg system-wide")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Audio extraction timed out")
        return False
    except Exception as error:
        logger.error(f"Error extracting audio: {error}")
        return False