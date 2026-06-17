from abc import ABC, abstractmethod

from agents.context import AgentContext
from agents.result import AgentResult


class BaseAgent(ABC):
    name: str

    @abstractmethod
    def can_handle(self, query: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def run(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError