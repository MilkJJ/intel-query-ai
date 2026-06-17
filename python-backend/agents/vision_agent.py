from pathlib import Path

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.result import AgentResult


class VisionAgent(BaseAgent):
    name = "vision"

    def can_handle(self, query: str) -> bool:
        normalized_query = query.lower().strip()
        return any(keyword in normalized_query for keyword in ["vision", "object", "frame", "scene", "see"])

    def run(self, context: AgentContext) -> AgentResult:
        video_path = context.video_path
        return AgentResult(
            agent=self.name,
            response="Vision agent selected. Frame and object analysis is the next feature to implement.",
            objects=[],
            note=f"Received video '{Path(video_path).name}' for future visual analysis.",
        )