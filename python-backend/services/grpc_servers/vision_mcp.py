"""
VisionMCP — gRPC service wrapper for VisionAgent.

Exposes frame analysis, object detection, graph detection, and OCR as gRPC services.
Runs independently and communicates with agents via gRPC protocol.

Proto Service:
  - AnalyzeFrames(video_path, sampling_interval, max_frames) -> frames + objects + ocr_text + graphs_detected
  - DetectObjects(video_path) -> objects + total_frames_analyzed
  - DetectGraphs(video_path) -> graphs_detected + graph_descriptions
  - ExtractText(video_path) -> text_snippets + total_frames_analyzed
  - Ping() -> health check
"""

import logging
import sys
from pathlib import Path

import grpc
from concurrent import futures

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from proto import vision_pb2, vision_pb2_grpc
from agents.vision_agent import VisionAgent
from agents.context import AgentContext

logger = logging.getLogger(__name__)


class VisionServicer(vision_pb2_grpc.VisionServiceServicer):
    """gRPC service implementation for vision analysis."""

    def __init__(self):
        """Initialize with VisionAgent."""
        self.vision_agent = VisionAgent()
        logger.info("VisionServicer initialized")

    def AnalyzeFrames(self, request, context):
        """
        Analyze video frames comprehensively.
        
        Args:
            request: AnalyzeFramesRequest with video_path, sampling_interval, max_frames
            context: gRPC context
            
        Returns:
            AnalyzeFramesResponse with frames, objects, ocr_text, graphs_detected
        """
        logger.info("AnalyzeFrames request: %s", request.video_path)
        try:
            # Create agent context
            agent_context = AgentContext(
                video_path=request.video_path,
                query="analyze_video"
            )
            agent_context.action = "analyze_video"
            agent_context.metadata = {
                "sampling_interval": request.sampling_interval or 5.0,
                "max_frames": request.max_frames or 12,
            }

            # Run vision analysis
            result = self.vision_agent.run(agent_context)

            # Extract frame data
            frames_list = []
            if result.metadata and "frames" in result.metadata:
                for frame_data in result.metadata.get("frames", []):
                    frame = vision_pb2.Frame(
                        timestamp=frame_data.get("timestamp", 0.0),
                        caption=frame_data.get("caption", ""),
                        objects=frame_data.get("objects", []),
                        on_screen_text=frame_data.get("on_screen_text", ""),
                    )
                    frames_list.append(frame)

            # Extract detected objects
            objects_list = []
            if result.objects:
                for obj_label in result.objects:
                    detected_obj = vision_pb2.DetectedObject(
                        label=obj_label,
                        count=1,
                    )
                    objects_list.append(detected_obj)

            # Build response
            response = vision_pb2.AnalyzeFramesResponse(
                frames=frames_list,
                objects=objects_list,
                ocr_text=result.metadata.get("on_screen_text", []) if result.metadata else [],
                graphs_detected=result.metadata.get("graphs_detected", False) if result.metadata else False,
                graph_descriptions=result.metadata.get("graph_descriptions", []) if result.metadata else [],
            )

            logger.info("✓ Frame analysis complete: %d frames, %d objects", len(frames_list), len(objects_list))
            return response

        except Exception as e:
            logger.error("AnalyzeFrames failed: %s", e)
            context.set_details(f"Frame analysis failed: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return vision_pb2.AnalyzeFramesResponse()

    def DetectObjects(self, request, context):
        """
        Detect objects in video frames.
        
        Args:
            request: DetectObjectsRequest with video_path
            context: gRPC context
            
        Returns:
            DetectObjectsResponse with objects, total_frames_analyzed
        """
        logger.info("DetectObjects request: %s", request.video_path)
        try:
            # Create agent context
            agent_context = AgentContext(
                video_path=request.video_path,
                query="detect_objects"
            )
            agent_context.action = "detect_objects"

            # Run detection
            result = self.vision_agent.run(agent_context)

            # Extract objects
            objects_list = []
            if result.objects:
                from collections import Counter
                counter = Counter(result.objects)
                for label, count in counter.most_common():
                    detected_obj = vision_pb2.DetectedObject(
                        label=label,
                        count=count,
                    )
                    objects_list.append(detected_obj)

            response = vision_pb2.DetectObjectsResponse(
                objects=objects_list,
                total_frames_analyzed=result.metadata.get("total_frames_analyzed", 0) if result.metadata else 0,
            )

            logger.info("✓ Object detection complete: %d objects", len(objects_list))
            return response

        except Exception as e:
            logger.error("DetectObjects failed: %s", e)
            context.set_details(f"Object detection failed: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return vision_pb2.DetectObjectsResponse()

    def DetectGraphs(self, request, context):
        """
        Detect graphs/charts in video frames.
        
        Args:
            request: DetectGraphsRequest with video_path
            context: gRPC context
            
        Returns:
            DetectGraphsResponse with graphs_detected, graph_descriptions, frames_with_graphs
        """
        logger.info("DetectGraphs request: %s", request.video_path)
        try:
            # Create agent context
            agent_context = AgentContext(
                video_path=request.video_path,
                query="detect_graphs"
            )
            agent_context.action = "detect_graphs"

            # Run detection
            result = self.vision_agent.run(agent_context)

            response = vision_pb2.DetectGraphsResponse(
                graphs_detected=result.metadata.get("graphs_detected", False) if result.metadata else False,
                graph_descriptions=result.metadata.get("graph_descriptions", []) if result.metadata else [],
                frames_with_graphs=result.metadata.get("frames_with_graphs", []) if result.metadata else [],
            )

            logger.info("✓ Graph detection complete: graphs_detected=%s", response.graphs_detected)
            return response

        except Exception as e:
            logger.error("DetectGraphs failed: %s", e)
            context.set_details(f"Graph detection failed: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return vision_pb2.DetectGraphsResponse()

    def ExtractText(self, request, context):
        """
        Extract on-screen text from video frames.
        
        Args:
            request: ExtractTextRequest with video_path
            context: gRPC context
            
        Returns:
            ExtractTextResponse with text_snippets, total_frames_analyzed
        """
        logger.info("ExtractText request: %s", request.video_path)
        try:
            # Create agent context
            agent_context = AgentContext(
                video_path=request.video_path,
                query="extract_text"
            )
            agent_context.action = "extract_text"

            # Run extraction
            result = self.vision_agent.run(agent_context)

            response = vision_pb2.ExtractTextResponse(
                text_snippets=result.metadata.get("on_screen_text", []) if result.metadata else [],
                total_frames_analyzed=result.metadata.get("total_frames_analyzed", 0) if result.metadata else 0,
            )

            logger.info("✓ Text extraction complete: %d snippets", len(response.text_snippets))
            return response

        except Exception as e:
            logger.error("ExtractText failed: %s", e)
            context.set_details(f"Text extraction failed: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return vision_pb2.ExtractTextResponse()

    def Ping(self, request, context):
        """Health check."""
        logger.info("Ping received: %s", request.message)
        return vision_pb2.PingResponse(
            message=f"Vision service alive. Echo: {request.message}"
        )


def serve(port=50052):
    """Start gRPC server."""
    logger.info("Starting VisionService on port %d", port)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    vision_pb2_grpc.add_VisionServiceServicer_to_server(
        VisionServicer(),
        server
    )

    server.add_insecure_port(f"0.0.0.0:{port}")
    server.start()
    logger.info("✓ VisionService listening on 0.0.0.0:%d", port)

    try:
        while True:
            import time
            time.sleep(86400)  # One day
    except KeyboardInterrupt:
        logger.info("Shutting down VisionService...")
        server.stop(grace_period=5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    serve()
