from agents.base import BaseAgent
from agents.generation_agent import GenerationAgent
from agents.report_agent import ReportAgent
from agents.router_agent import RouterAgent
from agents.transcription_agent import TranscriptionAgent
from agents.vision_agent import VisionAgent
from services.multimodal_pipeline import MultimodalPipeline


class AgentRegistry:
    """Registry of all available agents."""

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent by name."""
        self._agents[agent.name] = agent

    def get(self, name: str) -> BaseAgent | None:
        """Retrieve agent by name."""
        return self._agents.get(name)

    def all(self) -> list[BaseAgent]:
        """Get all registered agents."""
        return list(self._agents.values())

    def as_dict(self) -> dict[str, BaseAgent]:
        """Get agents as dict for external use."""
        return dict(self._agents)


def build_default_registry() -> AgentRegistry:
    """
    Build default agent registry with all core agents.
    
    Registration order:
      1. TranscriptionAgent
      2. VisionAgent
      3. MultimodalPipeline (service)
      4. GenerationAgent (depends on pipeline)
      5. ReportAgent (depends on transcription + vision + generation)
      6. RouterAgent (depends on all above)
    
    Returns:
        Fully initialized AgentRegistry
    """
    registry = AgentRegistry()

    # Core agents
    transcription_agent = TranscriptionAgent()
    vision_agent = VisionAgent()

    registry.register(transcription_agent)
    registry.register(vision_agent)

    # MultimodalPipeline (not an agent, but service)
    multimodal_pipeline = MultimodalPipeline(transcription_agent, vision_agent)

    # GenerationAgent (uses multimodal pipeline)
    generation_agent = GenerationAgent(multimodal_pipeline)
    registry.register(generation_agent)

    # ReportAgent (uses all agents)
    report_agent = ReportAgent(transcription_agent, vision_agent, generation_agent)
    registry.register(report_agent)

    # RouterAgent (uses registry to route queries)
    router_agent = RouterAgent(
        agents_registry=registry.as_dict(),
        transcription_agent=transcription_agent,
        vision_agent=vision_agent,
        generation_agent=generation_agent,
        report_agent=report_agent,
    )
    registry.register(router_agent)

    return registry