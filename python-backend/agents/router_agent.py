"""
RouterAgent — intent classification and agent routing with natural language support.

Responsibilities:
  1. Classify user query into intent type (TRANSCRIPTION, VISION, GENERATION, REPORT, COMBINED)
  2. Route to appropriate agents
  3. Support agent chaining for complex queries
  4. Execute agents with error handling
  5. Accumulate metadata through context

Intent Types:
  - TRANSCRIPTION: "transcript", "transcribe", "speech", "spoken"
  - VISION: "object", "detect", "graph", "chart", "visual", "on-screen text", "ocr"
  - GENERATION: "summarize", "summary", "overview", "recap", "insights"
  - REPORT: "pdf", "report", "generate", "create", "export", "ppt"
  - COMBINED: "analyze", "understand", "what does", "comprehensive"

Execution Flow:
  - Single intent: route directly to agent
  - COMBINED: vision → generation → report
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.result import AgentResult

if TYPE_CHECKING:
    from agents.transcription_agent import TranscriptionAgent
    from agents.vision_agent import VisionAgent
    from agents.generation_agent import GenerationAgent
    from agents.report_agent import ReportAgent

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Classification of user intent."""
    TRANSCRIPTION = "transcription"
    VISION = "vision"
    GENERATION = "generation"
    REPORT = "report"
    COMBINED = "combined"


class RouterAgent(BaseAgent):
    """Routes queries to specialist agents based on intent classification."""

    name = "router"

    def __init__(
        self,
        agents_registry: dict[str, BaseAgent],
        transcription_agent: TranscriptionAgent = None,
        vision_agent: VisionAgent = None,
        generation_agent: GenerationAgent = None,
        report_agent: ReportAgent = None,
    ):
        """
        Initialize router with agent registry and specific agent references.
        
        Args:
            agents_registry: dict of agent_name -> agent instance
            transcription_agent: TranscriptionAgent for audio extraction
            vision_agent: VisionAgent for frame analysis
            generation_agent: GenerationAgent for LLM-based insights
            report_agent: ReportAgent for PDF/PPT generation
        """
        self.agents_registry = agents_registry
        self.transcription_agent = transcription_agent
        self.vision_agent = vision_agent
        self.generation_agent = generation_agent
        self.report_agent = report_agent

    @property
    def actions(self) -> dict[str, any]:
        return {
            "route_query": self.route_query,
            "classify_intent": self.classify_intent,
        }

    def run(self, context: AgentContext) -> AgentResult:
        """Main entry point — route and execute query."""
        action = context.action or "route_query"
        handler = self.actions.get(action)
        if handler is None:
            raise ValueError(f"RouterAgent: unknown action '{action}'")
        return handler(context)

    def route_query(self, context: AgentContext) -> AgentResult:
        """
        Classify query intent and route to appropriate agent(s).
        
        Returns:
            AgentResult with response and accumulated metadata
        """
        query = context.query
        logger.info("RouterAgent routing query: %s", query)

        # Classify intent
        intent_type, intent_description = self._classify_intent(query)
        logger.info("Classified as: %s (%s)", intent_type.value, intent_description)

        # Route based on intent
        if intent_type == IntentType.TRANSCRIPTION:
            return self._execute_agent_action(
                "transcription", context, "get_transcript",
                "Transcription extracted from video"
            )

        elif intent_type == IntentType.VISION:
            return self._execute_agent_action(
                "vision", context, "analyze_video",
                "Vision analysis complete"
            )

        elif intent_type == IntentType.GENERATION:
            # Generation requires multimodal analysis first
            if self.vision_agent:
                self._execute_agent_action("vision", context, "analyze_video", "Vision analysis")
            return self._execute_agent_action(
                "generation", context, "generate_insights",
                "Insights generated from multimodal analysis"
            )

        elif intent_type == IntentType.REPORT:
            return self._execute_agent_action(
                "report", context, "generate_pdf",
                "Report generated"
            )

        elif intent_type == IntentType.COMBINED:
            # Full pipeline: vision → generation → report
            logger.info("COMBINED intent: executing full pipeline")
            if self.vision_agent:
                self._execute_agent_action("vision", context, "analyze_video", "Vision analysis")
            if self.generation_agent:
                self._execute_agent_action("generation", context, "generate_insights", "Generation")
            return self._execute_agent_action(
                "report", context, "generate_pdf",
                "Full analysis and report generated"
            )

        # Fallback
        logger.warning("Unknown intent, defaulting to transcription")
        return self._execute_agent_action(
            "transcription", context, "get_transcript",
            "Default transcription"
        )

    def classify_intent(self, context: AgentContext) -> AgentResult:
        """
        Standalone intent classifier for debugging.
        Returns a response with the classified intent.
        """
        query = context.query
        intent_type, intent_description = self._classify_intent(query)

        response = f"Intent: {intent_type.value}\nDescription: {intent_description}\nQuery: {query}"

        return AgentResult(
            agent=self.name,
            action="classify_intent",
            response=response,
            metadata={
                "intent_type": intent_type.value,
                "intent_description": intent_description,
            }
        )

    # ── Private Helpers ──────────────────────────────────────────────────────

    def _classify_intent(self, query: str) -> tuple[IntentType, str]:
        """
        Keyword-based intent classification.
        
        Returns:
            (IntentType, description)
        """
        query_lower = query.lower()

        # REPORT (highest priority — user explicitly wants export)
        if any(word in query_lower for word in ["pdf", "ppt", "powerpoint", "report", "export", "generate"]):
            if any(word in query_lower for word in ["pdf", "ppt", "powerpoint", "generate"]):
                return IntentType.REPORT, "User requesting report generation (PDF/PPT)"

        # VISION (next priority)
        if any(word in query_lower for word in ["object", "detect", "graph", "chart", "visual", "on-screen", "text", "ocr", "see", "show"]):
            return IntentType.VISION, "User asking about visual content (objects, text, graphs)"

        # TRANSCRIPTION (explicit request)
        if any(word in query_lower for word in ["transcript", "transcribe", "speech", "spoken", "audio", "say", "said"]):
            return IntentType.TRANSCRIPTION, "User requesting transcription"

        # COMBINED (full analysis request)
        if any(word in query_lower for word in ["analyze", "understand", "comprehensive", "full", "complete", "what does", "tell me", "explain"]):
            return IntentType.COMBINED, "User requesting comprehensive analysis"

        # GENERATION (summary/insights)
        if any(word in query_lower for word in ["summarize", "summary", "overview", "recap", "insights", "key points", "main", "gist"]):
            return IntentType.GENERATION, "User requesting summary and insights"

        # Default: assume generation/summary
        return IntentType.GENERATION, "Default: generating summary and insights"

    def _execute_agent_action(
        self,
        agent_name: str,
        context: AgentContext,
        action: str,
        fallback_response: str = "Execution complete"
    ) -> AgentResult:
        """
        Execute a specific agent action with error handling.
        
        Args:
            agent_name: name of agent in registry
            context: AgentContext to pass to agent
            action: action name within agent
            fallback_response: response if agent not found
            
        Returns:
            AgentResult from agent execution or error result
        """
        agent = self.agents_registry.get(agent_name)
        if agent is None:
            logger.error("Agent '%s' not found in registry", agent_name)
            return AgentResult(
                agent=self.name,
                action=action,
                response=f"Error: Agent '{agent_name}' not available",
            )

        saved_action = context.action
        try:
            context.action = action
            result = agent.run(context)
            logger.info("✓ Agent '%s' executed action '%s'", agent_name, action)
            # Store result in metadata for subsequent agents
            context.metadata[f"{agent_name}_result"] = result
            return result
        except Exception as e:
            logger.error("Agent '%s' failed: %s", agent_name, e)
            return AgentResult(
                agent=self.name,
                action=action,
                response=f"Error executing agent '{agent_name}': {str(e)}",
            )
        finally:
            context.action = saved_action
