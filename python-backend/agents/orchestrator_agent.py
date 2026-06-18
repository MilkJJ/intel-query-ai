"""
OrchestratorAgent — the central coordinator of the agent pipeline.

Responsibilities:
  1. Accept a user query via AgentContext.
  2. Classify intent using IntentClassifier → (agent_name, action, confidence).
  3. Look up the target specialist agent from the registry.
  4. Set context.action and delegate execution to that agent.
  5. Inject confidence into the returned AgentResult.

MCP integration note:
  The OrchestratorAgent itself can be registered as an MCP "router" tool.
  Each specialist agent's `actions` dict maps directly to individual MCP tools.
  Future work: replace classify_intent() with an MCP-hosted LLM classifier.
"""

import logging

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.intent_classifier import Intent, classify_intent
from agents.result import AgentResult


logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Routes queries to specialist agents based on classified intent.
    Not a BaseAgent subclass — it owns the agents rather than being one.
    """

    def __init__(self, agents: dict[str, BaseAgent]):
        self._agents = agents

    # ── Public API ────────────────────────────────────────────────────────────

    def route(self, query: str) -> tuple[BaseAgent, str, float]:
        """
        Classify the query and resolve it to (agent, action, confidence).
        Falls back to transcription/get_transcript if the intended agent is
        not registered.
        """
        intent: Intent = classify_intent(query)

        agent = self._agents.get(intent.agent)
        if agent is None:
            logger.warning(
                "Agent '%s' not registered. Falling back to transcription/get_transcript.",
                intent.agent,
            )
            agent = self._agents["transcription"]
            intent.action = "get_transcript"
            intent.confidence = 0.50

        logger.info(
            "Orchestrator routed → agent='%s'  action='%s'  confidence=%.2f",
            intent.agent,
            intent.action,
            intent.confidence,
        )
        return agent, intent.action, intent.confidence

    def handle(self, context: AgentContext) -> AgentResult:
        """
        Full pipeline: classify intent → dispatch → return structured result.
        """
        agent, action, confidence = self.route(context.query)
        context.action = action

        result = agent.run(context)
        result.confidence = confidence
        return result
