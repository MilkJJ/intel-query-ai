import logging

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.registry import AgentRegistry, build_default_registry
from agents.result import AgentResult


logger = logging.getLogger(__name__)


class AgentRouter:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def route(self, query: str) -> BaseAgent:
        for agent in self.registry.all():
            if agent.can_handle(query):
                return agent

        raise RuntimeError("No agent available to handle the query.")

    def handle(self, context: AgentContext) -> AgentResult:
        selected_agent = self.route(context.query)
        logger.info(f"Routing query to {selected_agent.name} agent")
        return selected_agent.run(context)


def build_agent_router() -> AgentRouter:
    return AgentRouter(build_default_registry())