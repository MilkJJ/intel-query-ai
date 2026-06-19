"""
TranscriptionMCP — gRPC service wrapper for TranscriptionAgent.

Exposes transcription and summarization as gRPC services.
Runs independently and communicates with agents via gRPC protocol.

Proto Service:
  - Transcribe(video_path) -> transcription + timestamps + language + duration
  - Summarize(transcript) -> summary + key_sentences
  - Ping() -> health check
"""

import logging
import sys
from pathlib import Path

import grpc
from concurrent import futures

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from proto import transcription_pb2, transcription_pb2_grpc
from agents.transcription_agent import TranscriptionAgent
from agents.context import AgentContext

logger = logging.getLogger(__name__)


class TranscriptionServicer(transcription_pb2_grpc.TranscriptionServiceServicer):
    """gRPC service implementation for transcription."""

    def __init__(self):
        """Initialize with TranscriptionAgent."""
        self.transcription_agent = TranscriptionAgent()
        logger.info("TranscriptionServicer initialized")

    def Transcribe(self, request, context):
        """
        Transcribe a video file.
        
        Args:
            request: TranscribeRequest with video_path, language_hint
            context: gRPC context
            
        Returns:
            TranscribeResponse with transcription, timestamps, language, duration
        """
        logger.info("Transcribe request: %s", request.video_path)
        try:
            # Create agent context
            agent_context = AgentContext(
                video_path=request.video_path,
                query="get_transcript"
            )
            agent_context.action = "get_transcript"

            # Run transcription
            result = self.transcription_agent.run(agent_context)

            # Build response
            response = transcription_pb2.TranscribeResponse(
                transcription=result.transcription,
                timestamps=result.metadata.get("timestamps", []) if result.metadata else [],
                language=result.language or "unknown",
                duration=result.duration or 0.0,
            )

            logger.info("✓ Transcription complete: %d chars", len(result.transcription))
            return response

        except Exception as e:
            logger.error("Transcribe failed: %s", e)
            context.set_details(f"Transcription failed: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return transcription_pb2.TranscribeResponse()

    def Summarize(self, request, context):
        """
        Summarize a transcript.
        
        Args:
            request: SummarizeRequest with transcript, max_sentences
            context: gRPC context
            
        Returns:
            SummarizeResponse with summary, key_sentences
        """
        logger.info("Summarize request: %d chars", len(request.transcript))
        try:
            # Simple heuristic summarization
            sentences = [
                s.strip() for s in request.transcript.split(".")
                if s.strip()
            ]

            max_sentences = request.max_sentences or 5
            summary_sentences = sentences[:max_sentences]
            summary = ". ".join(summary_sentences) + ("." if summary_sentences else "")

            response = transcription_pb2.SummarizeResponse(
                summary=summary,
                key_sentences=summary_sentences[:3],
            )

            logger.info("✓ Summarization complete: %d sentences", len(summary_sentences))
            return response

        except Exception as e:
            logger.error("Summarize failed: %s", e)
            context.set_details(f"Summarization failed: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return transcription_pb2.SummarizeResponse()

    def Ping(self, request, context):
        """Health check."""
        logger.info("Ping received: %s", request.message)
        return transcription_pb2.PingResponse(
            message=f"Transcription service alive. Echo: {request.message}"
        )


def serve(port=50051):
    """Start gRPC server."""
    logger.info("Starting TranscriptionService on port %d", port)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    transcription_pb2_grpc.add_TranscriptionServiceServicer_to_server(
        TranscriptionServicer(),
        server
    )

    server.add_insecure_port(f"0.0.0.0:{port}")
    server.start()
    logger.info("✓ TranscriptionService listening on 0.0.0.0:%d", port)

    try:
        while True:
            import time
            time.sleep(86400)  # One day
    except KeyboardInterrupt:
        logger.info("Shutting down TranscriptionService...")
        server.stop(grace_period=5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    serve()
