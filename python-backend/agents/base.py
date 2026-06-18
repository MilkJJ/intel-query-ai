from abc import ABC, abstractmethod
from typing import Callable

from agents.context import AgentContext
from agents.result import AgentResult


class BaseAgent(ABC):
    name: str

    @property
    def actions(self) -> dict[str, Callable[["AgentContext"], "AgentResult"]]:
        """
        Map of action_name -> handler method.
        Exposed for future MCP tool registration — each entry becomes
        a discrete MCP tool that the orchestrator can invoke by name.
        """
        return {}

    @abstractmethod
    def run(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError