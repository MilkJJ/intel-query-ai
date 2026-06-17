from agents.base import BaseAgent
from agents.generation_agent import GenerationAgent
from agents.transcription_agent import TranscriptionAgent
from agents.vision_agent import VisionAgent


class AgentRegistry:
    def __init__(self):
        self._agents: list[BaseAgent] = []

    def register(self, agent: BaseAgent) -> None:
        self._agents.append(agent)

    def all(self) -> list[BaseAgent]:
        return list(self._agents)


def build_default_registry() -> AgentRegistry:
    registry = AgentRegistry()
    transcription_agent = TranscriptionAgent()

    registry.register(VisionAgent())
    registry.register(transcription_agent)
    registry.register(GenerationAgent(transcription_agent))
    return registry