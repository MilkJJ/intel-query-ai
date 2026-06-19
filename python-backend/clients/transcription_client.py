"""
TranscriptionClient — gRPC client for transcription service.

Communicates with TranscriptionMCP gRPC server on port 50051.
Provides methods to:
  - Transcribe video files
  - Summarize transcripts
  - Health check (ping)
"""

import logging
import grpc

from proto import transcription_pb2, transcription_pb2_grpc

logger = logging.getLogger(__name__)


class TranscriptionClient:
    """Client for transcription gRPC service."""

    def __init__(self, host: str = "localhost", port: int = 50051):
        """
        Initialize client.
        
        Args:
            host: gRPC server host (default: localhost)
            port: gRPC server port (default: 50051)
        """
        self.host = host
        self.port = port
        self.channel = None
        self.stub = None

    def connect(self) -> bool:
        """
        Connect to gRPC server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            address = f"{self.host}:{self.port}"
            self.channel = grpc.insecure_channel(address)
            self.stub = transcription_pb2_grpc.TranscriptionServiceStub(self.channel)
            
            # Test connection with ping
            response = self.stub.Ping(transcription_pb2.PingRequest(message="test"))
            logger.info("✓ Connected to TranscriptionService at %s", address)
            return True
        except Exception as e:
            logger.error("Failed to connect to TranscriptionService: %s", e)
            return False

    def transcribe(self, video_path: str, language_hint: str = "") -> dict:
        """
        Transcribe a video file.
        
        Args:
            video_path: Path to video file
            language_hint: Optional language hint (e.g., "en", "es")
            
        Returns:
            Dict with transcription, timestamps, language, duration
            Returns empty dict on error
        """
        if not self.stub:
            logger.error("Not connected to TranscriptionService")
            return {}

        try:
            request = transcription_pb2.TranscribeRequest(
                video_path=video_path,
                language_hint=language_hint,
            )
            response = self.stub.Transcribe(request, timeout=300)  # 5 minute timeout
            
            logger.info("✓ Transcription complete: %d chars", len(response.transcription))
            return {
                "transcription": response.transcription,
                "timestamps": list(response.timestamps),
                "language": response.language,
                "duration": response.duration,
            }
        except grpc.RpcError as e:
            logger.error("Transcription RPC failed: %s", e.details())
            return {}
        except Exception as e:
            logger.error("Transcription failed: %s", e)
            return {}

    def summarize(self, transcript: str, max_sentences: int = 5) -> dict:
        """
        Summarize a transcript.
        
        Args:
            transcript: Full transcript text
            max_sentences: Maximum number of sentences in summary
            
        Returns:
            Dict with summary, key_sentences
            Returns empty dict on error
        """
        if not self.stub:
            logger.error("Not connected to TranscriptionService")
            return {}

        try:
            request = transcription_pb2.SummarizeRequest(
                transcript=transcript,
                max_sentences=max_sentences,
            )
            response = self.stub.Summarize(request, timeout=30)
            
            logger.info("✓ Summarization complete: %d chars", len(response.summary))
            return {
                "summary": response.summary,
                "key_sentences": list(response.key_sentences),
            }
        except grpc.RpcError as e:
            logger.error("Summarization RPC failed: %s", e.details())
            return {}
        except Exception as e:
            logger.error("Summarization failed: %s", e)
            return {}

    def close(self):
        """Close gRPC channel."""
        if self.channel:
            self.channel.close()
            logger.info("Closed TranscriptionService connection")
