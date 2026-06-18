from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentResult:
    agent: str
    action: str
    response: str
    confidence: float = 1.0
    transcription: str = ""
    language: str = "unknown"
    duration: float = 0.0
    objects: list[str] = field(default_factory=list)
    frames: list[dict] = field(default_factory=list)
    note: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)