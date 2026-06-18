from agents.base import BaseAgent
from agents.report_agent import ReportAgent
from agents.transcription_agent import TranscriptionAgent
from agents.vision_agent import VisionAgent


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    def get(self, name: str) -> BaseAgent | None:
        return self._agents.get(name)

    def all(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def as_dict(self) -> dict[str, BaseAgent]:
        return dict(self._agents)


def build_default_registry() -> AgentRegistry:
    registry = AgentRegistry()
    transcription_agent = TranscriptionAgent()

    registry.register(transcription_agent)
    registry.register(VisionAgent())
    registry.register(ReportAgent(transcription_agent))
    return registry