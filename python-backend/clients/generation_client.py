"""
GenerationClient — gRPC client for generation service.

Communicates with GenerationMCP gRPC server on port 50053.
Provides methods to:
  - Generate insights from multimodal analysis
  - Generate summaries
  - Answer queries
  - Health check (ping)
"""

import logging
import grpc

from proto import generation_pb2, generation_pb2_grpc

logger = logging.getLogger(__name__)


class GenerationClient:
    """Client for generation gRPC service."""

    def __init__(self, host: str = "localhost", port: int = 50053):
        """
        Initialize client.
        
        Args:
            host: gRPC server host (default: localhost)
            port: gRPC server port (default: 50053)
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
            self.stub = generation_pb2_grpc.GenerationServiceStub(self.channel)
            
            # Test connection with ping
            response = self.stub.Ping(generation_pb2.PingRequest(message="test"))
            logger.info("✓ Connected to GenerationService at %s", address)
            return True
        except Exception as e:
            logger.error("Failed to connect to GenerationService: %s", e)
            return False

    def generate_insights(
        self,
        transcript: str,
        detected_objects: list[str] = None,
        ocr_text: list[str] = None,
        graphs_detected: bool = False,
        graph_descriptions: list[str] = None,
    ) -> dict:
        """
        Generate insights from multimodal analysis.
        
        Args:
            transcript: Full transcription text
            detected_objects: List of detected object labels
            ocr_text: List of extracted text snippets
            graphs_detected: Whether graphs were detected
            graph_descriptions: Descriptions of detected graphs
            
        Returns:
            Dict with summary, key_topics, key_insights, conclusion
            Returns empty dict on error
        """
        if not self.stub:
            logger.error("Not connected to GenerationService")
            return {}

        try:
            request = generation_pb2.GenerateInsightsRequest(
                transcript=transcript,
                detected_objects=detected_objects or [],
                ocr_text=ocr_text or [],
                graphs_detected=graphs_detected,
                graph_descriptions=graph_descriptions or [],
            )
            response = self.stub.GenerateInsights(request, timeout=120)  # 2 minute timeout
            
            insights = response.insights
            logger.info("✓ Insights generated: %d topics, %d insights", 
                       len(insights.key_topics), len(insights.key_insights))
            return {
                "summary": insights.summary,
                "key_topics": list(insights.key_topics),
                "key_insights": list(insights.key_insights),
                "conclusion": insights.conclusion,
            }
        except grpc.RpcError as e:
            logger.error("Generate insights RPC failed: %s", e.details())
            return {}
        except Exception as e:
            logger.error("Generate insights failed: %s", e)
            return {}

    def generate_summary(self, transcript: str, max_chars: int = 400) -> dict:
        """
        Generate summary from transcript.
        
        Args:
            transcript: Full transcript text
            max_chars: Maximum characters in summary
            
        Returns:
            Dict with summary
            Returns empty dict on error
        """
        if not self.stub:
            logger.error("Not connected to GenerationService")
            return {}

        try:
            request = generation_pb2.GenerateSummaryRequest(
                transcript=transcript,
                max_chars=max_chars,
            )
            response = self.stub.GenerateSummary(request, timeout=30)
            
            logger.info("✓ Summary generated: %d chars", len(response.summary))
            return {
                "summary": response.summary,
            }
        except grpc.RpcError as e:
            logger.error("Generate summary RPC failed: %s", e.details())
            return {}
        except Exception as e:
            logger.error("Generate summary failed: %s", e)
            return {}

    def answer_query(
        self,
        query: str,
        transcript: str,
        detected_objects: list[str] = None,
        ocr_text: list[str] = None,
        graphs_detected: bool = False,
    ) -> dict:
        """
        Answer a user query based on video analysis.
        
        Args:
            query: User query text
            transcript: Full transcript text
            detected_objects: List of detected object labels
            ocr_text: List of extracted text snippets
            graphs_detected: Whether graphs were detected
            
        Returns:
            Dict with answer
            Returns empty dict on error
        """
        if not self.stub:
            logger.error("Not connected to GenerationService")
            return {}

        try:
            request = generation_pb2.AnswerQueryRequest(
                query=query,
                transcript=transcript,
                detected_objects=detected_objects or [],
                ocr_text=ocr_text or [],
                graphs_detected=graphs_detected,
            )
            response = self.stub.AnswerQuery(request, timeout=120)
            
            logger.info("✓ Query answered")
            return {
                "answer": response.answer,
            }
        except grpc.RpcError as e:
            logger.error("Answer query RPC failed: %s", e.details())
            return {}
        except Exception as e:
            logger.error("Answer query failed: %s", e)
            return {}

    def close(self):
        """Close gRPC channel."""
        if self.channel:
            self.channel.close()
            logger.info("Closed GenerationService connection")
