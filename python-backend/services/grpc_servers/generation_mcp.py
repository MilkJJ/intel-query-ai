"""
GenerationMCP — gRPC service wrapper for GenerationAgent.

Exposes LLM-based insight generation as gRPC services.
Runs independently and communicates with agents via gRPC protocol.

Proto Service:
  - GenerateInsights(transcript, objects, ocr_text, graphs_detected) -> insights
  - GenerateSummary(transcript) -> summary
  - AnswerQuery(query, transcript, objects) -> answer
  - Ping() -> health check
"""

import logging
import sys
from pathlib import Path

import grpc
from concurrent import futures

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from proto import generation_pb2, generation_pb2_grpc
from agents.generation_agent import GenerationAgent
from agents.context import AgentContext
from services.multimodal_pipeline import MultimodalPipeline
from agents.transcription_agent import TranscriptionAgent
from agents.vision_agent import VisionAgent

logger = logging.getLogger(__name__)


class GenerationServicer(generation_pb2_grpc.GenerationServiceServicer):
    """gRPC service implementation for generation/insights."""

    def __init__(self):
        """Initialize with GenerationAgent."""
        transcription_agent = TranscriptionAgent()
        vision_agent = VisionAgent()
        multimodal_pipeline = MultimodalPipeline(transcription_agent, vision_agent)
        self.generation_agent = GenerationAgent(multimodal_pipeline)
        logger.info("GenerationServicer initialized")

    def GenerateInsights(self, request, context):
        """
        Generate insights from multimodal analysis.
        
        Args:
            request: GenerateInsightsRequest with transcript, objects, ocr_text, graphs_detected
            context: gRPC context
            
        Returns:
            GenerateInsightsResponse with insights (summary, key_topics, key_insights, conclusion)
        """
        logger.info("GenerateInsights request: %d chars transcript", len(request.transcript))
        try:
            # Build multimodal analysis from request
            analysis = {
                "transcript": request.transcript,
                "objects": [{"label": obj, "count": 1} for obj in request.detected_objects],
                "ocr_text": list(request.ocr_text),
                "graphs_detected": request.graphs_detected,
                "graph_descriptions": list(request.graph_descriptions),
            }

            # Create agent context with pre-built analysis
            agent_context = AgentContext(
                video_path="",  # Not needed, we have analysis
                query="generate_insights"
            )
            agent_context.action = "generate_insights"
            agent_context.metadata["multimodal_analysis"] = analysis

            # Run generation
            result = self.generation_agent.run(agent_context)
            insights_data = result.metadata or {}

            # Build response
            insights_msg = generation_pb2.InsightMessage(
                summary=insights_data.get("summary", "No summary available"),
                key_topics=list(insights_data.get("key_topics", [])),
                key_insights=list(insights_data.get("key_insights", [])),
                conclusion=insights_data.get("conclusion", ""),
            )

            response = generation_pb2.GenerateInsightsResponse(
                insights=insights_msg
            )

            logger.info("✓ Insights generated: %d topics, %d insights", 
                       len(insights_msg.key_topics), len(insights_msg.key_insights))
            return response

        except Exception as e:
            logger.error("GenerateInsights failed: %s", e)
            context.set_details(f"Insight generation failed: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return generation_pb2.GenerateInsightsResponse()

    def GenerateSummary(self, request, context):
        """
        Generate summary from transcript.
        
        Args:
            request: GenerateSummaryRequest with transcript, max_chars
            context: gRPC context
            
        Returns:
            GenerateSummaryResponse with summary
        """
        logger.info("GenerateSummary request: %d chars", len(request.transcript))
        try:
            # Simple heuristic: take first max_chars characters or first 5 sentences
            max_chars = request.max_chars or 400
            
            sentences = [s.strip() for s in request.transcript.split(".") if s.strip()]
            summary_sentences = sentences[:5]
            summary = ". ".join(summary_sentences)
            if len(summary) > max_chars:
                summary = summary[:max_chars].rsplit(" ", 1)[0] + "..."
            
            response = generation_pb2.GenerateSummaryResponse(
                summary=summary
            )

            logger.info("✓ Summary generated: %d chars", len(response.summary))
            return response

        except Exception as e:
            logger.error("GenerateSummary failed: %s", e)
            context.set_details(f"Summary generation failed: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return generation_pb2.GenerateSummaryResponse()

    def AnswerQuery(self, request, context):
        """
        Answer a user query based on video analysis.
        
        Args:
            request: AnswerQueryRequest with query, transcript, objects, ocr_text, graphs_detected
            context: gRPC context
            
        Returns:
            AnswerQueryResponse with answer
        """
        logger.info("AnswerQuery request: %s", request.query)
        try:
            # Build multimodal analysis from request
            analysis = {
                "transcript": request.transcript,
                "objects": [{"label": obj, "count": 1} for obj in request.detected_objects],
                "ocr_text": list(request.ocr_text),
                "graphs_detected": request.graphs_detected,
            }

            # Create agent context
            agent_context = AgentContext(
                video_path="",
                query=request.query
            )
            agent_context.action = "answer_query"
            agent_context.metadata["multimodal_analysis"] = analysis

            # Run query answering
            result = self.generation_agent.run(agent_context)

            response = generation_pb2.AnswerQueryResponse(
                answer=result.response
            )

            logger.info("✓ Query answered")
            return response

        except Exception as e:
            logger.error("AnswerQuery failed: %s", e)
            context.set_details(f"Query answering failed: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return generation_pb2.AnswerQueryResponse()

    def Ping(self, request, context):
        """Health check."""
        logger.info("Ping received: %s", request.message)
        return generation_pb2.PingResponse(
            message=f"Generation service alive. Echo: {request.message}"
        )


def serve(port=50053):
    """Start gRPC server."""
    logger.info("Starting GenerationService on port %d", port)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    generation_pb2_grpc.add_GenerationServiceServicer_to_server(
        GenerationServicer(),
        server
    )

    server.add_insecure_port(f"0.0.0.0:{port}")
    server.start()
    logger.info("✓ GenerationService listening on 0.0.0.0:%d", port)

    try:
        while True:
            import time
            time.sleep(86400)  # One day
    except KeyboardInterrupt:
        logger.info("Shutting down GenerationService...")
        server.stop(grace_period=5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    serve()
