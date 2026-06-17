from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentContext:
    video_path: str
    query: str
    session_id: str | None = None
    transcript: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)