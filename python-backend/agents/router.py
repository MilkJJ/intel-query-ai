import logging

from agents.context import AgentContext
from agents.orchestrator_agent import OrchestratorAgent
from agents.registry import AgentRegistry, build_default_registry
from agents.result import AgentResult


logger = logging.getLogger(__name__)


class AgentRouter:
    """
    Thin entry-point that delegates all routing decisions to OrchestratorAgent.
    Keeping this wrapper preserves the existing call-site in main.py.
    """

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self._orchestrator = OrchestratorAgent(registry.as_dict())

    def handle(self, context: AgentContext) -> AgentResult:
        return self._orchestrator.handle(context)


def build_agent_router() -> AgentRouter:
    return AgentRouter(build_default_registry())