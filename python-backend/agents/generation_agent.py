"""
GenerationAgent — LLM-based insight generation from multimodal analysis.

Responsibilities:
  1. Accept structured multimodal analysis (from MultimodalPipeline)
  2. Use local LLM (Llama.cpp via llama-cpp-python) to generate:
     - Executive summary
     - Key topics/themes
     - Key insights
     - Conclusions
  3. Provide heuristic fallback if LLM unavailable
  4. Return structured insights for downstream agents

LLM Integration:
  - Phase 4: Full Llama.cpp integration with llama-cpp-python
  - Supports TinyLlama, Mistral, and other GGUF-quantized models
  - Auto-fallback to heuristics if model not available
  - Configurable model path and auto-download from HuggingFace
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.result import AgentResult

if TYPE_CHECKING:
    from services.multimodal_pipeline import MultimodalPipeline

logger = logging.getLogger(__name__)


class GenerationAgent(BaseAgent):
    """Generate LLM-based insights from multimodal analysis."""

    name = "generation"

    def __init__(self, multimodal_pipeline: MultimodalPipeline = None):
        """
        Initialize GenerationAgent.
        
        Args:
            multimodal_pipeline: MultimodalPipeline instance for analysis
        """
        self.multimodal_pipeline = multimodal_pipeline
        
        # Initialize LLM service (Phase 4)
        from services.llama_service import get_llama_service
        self.llm_service = get_llama_service(enable_llm=True)

    @property
    def actions(self) -> dict[str, any]:
        return {
            "generate_insights": self.generate_insights,
            "generate_summary": self.generate_summary,
            "answer_query": self.answer_query,
        }

    def run(self, context: AgentContext) -> AgentResult:
        """Main entry point."""
        action = context.action or "generate_insights"
        handler = self.actions.get(action)
        if handler is None:
            raise ValueError(f"GenerationAgent: unknown action '{action}'")
        return handler(context)

    def generate_insights(self, context: AgentContext) -> AgentResult:
        """
        Generate comprehensive insights from multimodal analysis.
        
        Returns:
            AgentResult with structured insights
        """
        logger.info("GenerationAgent generating insights from multimodal data")

        # Get or create multimodal analysis
        analysis = context.metadata.get("multimodal_analysis")
        if not analysis:
            if self.multimodal_pipeline:
                logger.info("No cached analysis, running multimodal pipeline")
                analysis = self.multimodal_pipeline.analyze(context)
                context.metadata["multimodal_analysis"] = analysis
            else:
                logger.warning("No multimodal pipeline available")
                analysis = {}

        # Generate insights using LLM (Phase 4) or heuristic fallback
        if self.llm_service and self.llm_service.is_ready():
            logger.info("Using LLM service for insight generation")
            insights = self.llm_service.generate_insights(
                transcript=analysis.get("transcript", ""),
                objects=[obj.get("label", "") for obj in analysis.get("objects", [])],
                ocr_text=analysis.get("ocr_text", []),
                graphs_detected=analysis.get("graphs_detected", False),
            )
        else:
            logger.info("LLM service unavailable, using heuristic insight generation")
            insights = self._generate_insights_heuristic(analysis)

        context.metadata["generated_insights"] = insights

        # Format response
        response = self._format_insights_response(insights)

        return AgentResult(
            agent=self.name,
            action="generate_insights",
            response=response,
            metadata=insights,
        )

    def generate_summary(self, context: AgentContext) -> AgentResult:
        """Generate executive summary."""
        logger.info("GenerationAgent generating summary")

        analysis = context.metadata.get("multimodal_analysis")
        if not analysis:
            if self.multimodal_pipeline:
                analysis = self.multimodal_pipeline.analyze(context)
            else:
                analysis = {}

        # Use LLM if available
        if self.llm_service and self.llm_service.is_ready():
            logger.info("Using LLM service for summary generation")
            summary = self.llm_service.generate_summary(
                transcript=analysis.get("transcript", ""),
                max_tokens=300
            )
        else:
            logger.info("LLM service unavailable, using heuristic summary")
            summary = (analysis.get("transcript", ""))[:300] if analysis.get("transcript") else "No content available"

        return AgentResult(
            agent=self.name,
            action="generate_summary",
            response=summary,
            metadata={"summary": summary},
        )

    def answer_query(self, context: AgentContext) -> AgentResult:
        """Answer a specific user query based on analysis."""
        logger.info("GenerationAgent answering query: %s", context.query)

        analysis = context.metadata.get("multimodal_analysis")
        if not analysis:
            if self.multimodal_pipeline:
                analysis = self.multimodal_pipeline.analyze(context)
            else:
                analysis = {}

        # Use LLM if available, otherwise heuristic
        if self.llm_service and self.llm_service.is_ready():
            logger.info("Using LLM service to answer query")
            response = self.llm_service.answer_query(
                query=context.query,
                transcript=analysis.get("transcript", ""),
                objects=[obj.get("label", "") for obj in analysis.get("objects", [])],
                ocr_text=analysis.get("ocr_text", []),
            )
        else:
            logger.info("LLM service unavailable, using heuristic answer")
            response = self._answer_with_heuristic(analysis, context.query)

        return AgentResult(
            agent=self.name,
            action="answer_query",
            response=response,
            metadata={"query": context.query},
        )

    # ── Heuristic Insight Generation (fallback, before LLM) ──────────────────

    def _generate_insights_heuristic(self, analysis: dict[str, Any]) -> dict[str, Any]:
        """
        Generate insights using heuristic rules (no LLM).
        Will be augmented with LLM in Phase 4.
        """
        transcript = analysis.get("transcript", "")
        objects = analysis.get("objects", [])
        ocr_text = analysis.get("ocr_text", [])
        graphs_detected = analysis.get("graphs_detected", False)

        # Summary: first 400 chars of transcript
        summary = transcript[:400] if transcript else "No audio content found"
        if len(transcript) > 400:
            summary += "..."

        # Key topics: extract from objects and OCR
        key_topics = []
        if objects:
            key_topics.extend([obj["label"] for obj in objects[:3]])
        if ocr_text:
            key_topics.extend(ocr_text[:2])
        if graphs_detected:
            key_topics.append("Data visualization")

        # Key insights: heuristic observations
        insights = []
        if len(objects) > 0:
            insights.append(f"Detected {len(objects)} types of objects in the video")
        if graphs_detected:
            insights.append("Video contains charts or data visualizations")
        if len(ocr_text) > 0:
            insights.append("Video contains on-screen text or captions")
        if len(transcript) > 100:
            insights.append("Comprehensive audio narration throughout the video")

        if not insights:
            insights = ["Limited visual or audio content detected"]

        # Conclusion
        conclusion = f"Video analyzed with {len(objects)} objects, {len(ocr_text)} text elements, and graph detection: {graphs_detected}"

        return {
            "summary": summary,
            "key_topics": list(set(key_topics))[:5],  # Dedupe and limit
            "key_insights": insights[:3],  # Top 3 insights
            "conclusion": conclusion,
        }

    def _answer_with_heuristic(self, analysis: dict[str, Any], query: str) -> str:
        """Answer user query using heuristic matching (no LLM)."""
        query_lower = query.lower()
        transcript = analysis.get("transcript", "")
        objects = analysis.get("objects", [])
        graphs_detected = analysis.get("graphs_detected", False)

        # Answer based on query keywords
        if any(word in query_lower for word in ["object", "detect", "show"]):
            if objects:
                obj_list = ", ".join([obj["label"] for obj in objects])
                return f"Detected objects: {obj_list}"
            return "No objects detected"

        if any(word in query_lower for word in ["graph", "chart"]):
            if graphs_detected:
                return "Yes, the video contains graphs or charts"
            return "No graphs or charts detected"

        if any(word in query_lower for word in ["summarize", "summary", "what"]):
            return transcript[:500] if transcript else "No content to summarize"

        return f"Query: {query}\nTranscript excerpt: {transcript[:300]}"


    def _format_insights_response(self, insights: dict[str, Any]) -> str:
        """Format insights dict into readable response."""
        parts = [
            f"Summary:\n{insights.get('summary', 'N/A')}",
            f"\nKey Topics:\n- " + "\n- ".join(insights.get("key_topics", [])),
            f"\nKey Insights:\n- " + "\n- ".join(insights.get("key_insights", [])),
            f"\nConclusion:\n{insights.get('conclusion', 'N/A')}",
        ]
        return "\n".join(parts)