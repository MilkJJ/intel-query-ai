"""
VisionClient — gRPC client for vision service.

Communicates with VisionMCP gRPC server on port 50052.
Provides methods to:
  - Analyze video frames comprehensively
  - Detect objects in frames
  - Detect graphs/charts
  - Extract on-screen text (OCR)
  - Health check (ping)
"""

import logging
import grpc

from proto import vision_pb2, vision_pb2_grpc

logger = logging.getLogger(__name__)


class VisionClient:
    """Client for vision gRPC service."""

    def __init__(self, host: str = "localhost", port: int = 50052):
        """
        Initialize client.
        
        Args:
            host: gRPC server host (default: localhost)
            port: gRPC server port (default: 50052)
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
            self.stub = vision_pb2_grpc.VisionServiceStub(self.channel)
            
            # Test connection with ping
            response = self.stub.Ping(vision_pb2.PingRequest(message="test"))
            logger.info("✓ Connected to VisionService at %s", address)
            return True
        except Exception as e:
            logger.error("Failed to connect to VisionService: %s", e)
            return False

    def analyze_frames(self, video_path: str, sampling_interval: float = 5.0, max_frames: int = 12) -> dict:
        """
        Analyze video frames comprehensively.
        
        Args:
            video_path: Path to video file
            sampling_interval: Seconds between frame samples (default: 5.0)
            max_frames: Maximum number of frames to analyze (default: 12)
            
        Returns:
            Dict with frames, objects, ocr_text, graphs_detected, graph_descriptions
            Returns empty dict on error
        """
        if not self.stub:
            logger.error("Not connected to VisionService")
            return {}

        try:
            request = vision_pb2.AnalyzeFramesRequest(
                video_path=video_path,
                sampling_interval=sampling_interval,
                max_frames=max_frames,
            )
            response = self.stub.AnalyzeFrames(request, timeout=600)  # 10 minute timeout
            
            logger.info("✓ Frame analysis complete: %d frames, %d objects", 
                       len(response.frames), len(response.objects))
            return {
                "frames": [
                    {
                        "timestamp": f.timestamp,
                        "caption": f.caption,
                        "objects": list(f.objects),
                        "on_screen_text": f.on_screen_text,
                    }
                    for f in response.frames
                ],
                "objects": [
                    {
                        "label": o.label,
                        "count": o.count,
                        "frames_appear_in": list(o.frames_appear_in),
                    }
                    for o in response.objects
                ],
                "ocr_text": list(response.ocr_text),
                "graphs_detected": response.graphs_detected,
                "graph_descriptions": list(response.graph_descriptions),
            }
        except grpc.RpcError as e:
            logger.error("Frame analysis RPC failed: %s", e.details())
            return {}
        except Exception as e:
            logger.error("Frame analysis failed: %s", e)
            return {}

    def detect_objects(self, video_path: str) -> dict:
        """
        Detect objects in video frames.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict with objects, total_frames_analyzed
            Returns empty dict on error
        """
        if not self.stub:
            logger.error("Not connected to VisionService")
            return {}

        try:
            request = vision_pb2.DetectObjectsRequest(video_path=video_path)
            response = self.stub.DetectObjects(request, timeout=300)
            
            logger.info("✓ Object detection complete: %d objects from %d frames", 
                       len(response.objects), response.total_frames_analyzed)
            return {
                "objects": [
                    {"label": o.label, "count": o.count}
                    for o in response.objects
                ],
                "total_frames_analyzed": response.total_frames_analyzed,
            }
        except grpc.RpcError as e:
            logger.error("Object detection RPC failed: %s", e.details())
            return {}
        except Exception as e:
            logger.error("Object detection failed: %s", e)
            return {}

    def detect_graphs(self, video_path: str) -> dict:
        """
        Detect graphs/charts in video frames.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict with graphs_detected, graph_descriptions, frames_with_graphs
            Returns empty dict on error
        """
        if not self.stub:
            logger.error("Not connected to VisionService")
            return {}

        try:
            request = vision_pb2.DetectGraphsRequest(video_path=video_path)
            response = self.stub.DetectGraphs(request, timeout=300)
            
            logger.info("✓ Graph detection complete: graphs_detected=%s", response.graphs_detected)
            return {
                "graphs_detected": response.graphs_detected,
                "graph_descriptions": list(response.graph_descriptions),
                "frames_with_graphs": list(response.frames_with_graphs),
            }
        except grpc.RpcError as e:
            logger.error("Graph detection RPC failed: %s", e.details())
            return {}
        except Exception as e:
            logger.error("Graph detection failed: %s", e)
            return {}

    def extract_text(self, video_path: str) -> dict:
        """
        Extract on-screen text from video frames (OCR).
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict with text_snippets, total_frames_analyzed
            Returns empty dict on error
        """
        if not self.stub:
            logger.error("Not connected to VisionService")
            return {}

        try:
            request = vision_pb2.ExtractTextRequest(video_path=video_path)
            response = self.stub.ExtractText(request, timeout=300)
            
            logger.info("✓ Text extraction complete: %d snippets from %d frames", 
                       len(response.text_snippets), response.total_frames_analyzed)
            return {
                "text_snippets": list(response.text_snippets),
                "total_frames_analyzed": response.total_frames_analyzed,
            }
        except grpc.RpcError as e:
            logger.error("Text extraction RPC failed: %s", e.details())
            return {}
        except Exception as e:
            logger.error("Text extraction failed: %s", e)
            return {}

    def close(self):
        """Close gRPC channel."""
        if self.channel:
            self.channel.close()
            logger.info("Closed VisionService connection")
