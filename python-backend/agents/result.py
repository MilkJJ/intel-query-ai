from dataclasses import dataclass, field


@dataclass(slots=True)
class AgentResult:
    agent: str
    response: str
    transcription: str = ""
    language: str = "unknown"
    duration: float = 0
    objects: list[str] = field(default_factory=list)
    note: str | None = None