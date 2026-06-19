"""
MultimodalPipeline — orchestrates multimodal extraction and builds structured output.

Responsibilities:
  1. Extract transcription + timestamps
  2. Sample and analyze frames (captions, objects, text, charts)
  3. Aggregate results into unified structured analysis
  4. Store intermediate results in context.metadata for downstream agents

Output Schema:
{
  "transcript": "full transcription",
  "timestamps": [0.0, 5.2, 10.1, ...],
  "scenes": [
    {
      "timestamp": 0.0,
      "caption": "...",
      "detected_objects": ["object1", "object2"],
      "on_screen_text": "..."
    },
    ...
  ],
  "objects": [
    {"label": "person", "count": 3},
    {"label": "laptop", "count": 1},
    ...
  ],
  "ocr_text": ["text from frame 1", "text from frame 2", ...],
  "graphs_detected": true/false,
  "graph_descriptions": ["chart showing trends", ...],
  "language": "en",
  "duration": 120.5,
  "source": "video.mp4"
}
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path
from typing import Any

from agents.context import AgentContext
from agents.result import AgentResult

logger = logging.getLogger(__name__)


class MultimodalPipeline:
    """Coordinates multimodal extraction from video files."""

    def __init__(self, transcription_agent, vision_agent):
        self.transcription_agent = transcription_agent
        self.vision_agent = vision_agent

    def analyze(self, context: AgentContext) -> dict[str, Any]:
        """
        Run full multimodal pipeline:
        1. Extract transcription
        2. Analyze frames (objects, captions, text)
        3. Build structured output
        
        Returns structured analysis dict conforming to schema above.
        """
        logger.info("Starting multimodal pipeline analysis for: %s", context.video_path)

        # Step 1: Transcription
        transcription_result = self._extract_transcription(context)
        transcript = transcription_result.transcription
        language = transcription_result.language
        duration = transcription_result.duration
        timestamps = transcription_result.metadata.get("timestamps", []) if transcription_result.metadata else []

        # Step 2: Vision analysis
        vision_result = self._extract_vision_analysis(context)
        scenes = vision_result.metadata.get("scenes", []) if vision_result and vision_result.metadata else []
        detected_objects_raw = vision_result.metadata.get("detected_objects", []) if vision_result and vision_result.metadata else []
        on_screen_text = vision_result.metadata.get("on_screen_text", []) if vision_result and vision_result.metadata else []
        graphs_detected = vision_result.metadata.get("graphs_detected", False) if vision_result and vision_result.metadata else False
        graph_descriptions = vision_result.metadata.get("graph_descriptions", []) if vision_result and vision_result.metadata else []

        # Step 3: Build structured output
        structured_output = self._build_structured_output(
            transcript=transcript,
            timestamps=timestamps,
            scenes=scenes,
            detected_objects_raw=detected_objects_raw,
            ocr_text=on_screen_text,
            graphs_detected=graphs_detected,
            graph_descriptions=graph_descriptions,
            language=language,
            duration=duration,
            source=Path(context.video_path).name,
        )

        logger.info("✓ Multimodal pipeline analysis complete")
        return structured_output

    def _extract_transcription(self, context: AgentContext) -> AgentResult:
        """Extract audio transcription using TranscriptionAgent."""
        logger.info("Extracting transcription...")
        saved_action = context.action
        try:
            context.action = "get_transcript"
            result = self.transcription_agent.run(context)
            logger.info("✓ Transcription extracted: %d chars", len(result.transcription))
            return result
        finally:
            context.action = saved_action

    def _extract_vision_analysis(self, context: AgentContext) -> AgentResult | None:
        """Analyze frames using VisionAgent."""
        if self.vision_agent is None:
            logger.warning("VisionAgent not available, skipping vision analysis")
            return None

        logger.info("Analyzing frames...")
        saved_action = context.action
        try:
            context.action = "analyze_video"
            result = self.vision_agent.run(context)
            logger.info("✓ Vision analysis complete")
            return result
        except Exception as e:
            logger.warning("Vision analysis failed: %s, continuing without visual data", e)
            return None
        finally:
            context.action = saved_action

    def _build_structured_output(
        self,
        transcript: str,
        timestamps: list[float],
        scenes: list[dict],
        detected_objects_raw: list[str],
        ocr_text: list[str],
        graphs_detected: bool,
        graph_descriptions: list[str],
        language: str,
        duration: float,
        source: str,
    ) -> dict[str, Any]:
        """Aggregate all analysis into unified structured output."""

        # Aggregate objects with counts
        objects = self._extract_objects(detected_objects_raw)

        # Clean OCR text
        ocr_text = [t for t in ocr_text if t and str(t).strip()]

        structured = {
            "transcript": transcript,
            "timestamps": timestamps,
            "scenes": scenes,
            "objects": objects,
            "ocr_text": ocr_text,
            "graphs_detected": graphs_detected,
            "graph_descriptions": graph_descriptions,
            "language": language,
            "duration": duration,
            "source": source,
        }

        logger.info(
            "Structured output: %d scenes, %d objects, %d OCR texts, graphs_detected=%s",
            len(scenes),
            len(objects),
            len(ocr_text),
            graphs_detected,
        )

        return structured

    def _extract_objects(self, detected_objects_raw: list[str]) -> list[dict[str, Any]]:
        """
        Convert flat list of objects into list of {label, count} dicts.
        Example: ["person", "laptop", "person"] → [{"label": "person", "count": 2}, {"label": "laptop", "count": 1}]
        """
        if not detected_objects_raw:
            return []

        counter = Counter(detected_objects_raw)
        objects = [{"label": label, "count": count} for label, count in counter.most_common()]
        return objects
