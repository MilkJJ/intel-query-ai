from typing import Any

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    format: str
    title: str = "Video AI Report"
    filename: str | None = None
    query: str
    agent: str
    response: str
    transcription: str = ""
    transcript_summary: str = ""
    detected_objects: list[str] = Field(default_factory=list)
    frame_text: list[str] = Field(default_factory=list)
    language: str = "unknown"
    duration: float = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    """Structured response returned by the /query endpoint."""
    success: bool
    filename: str
    query: str
    # Orchestrator fields
    agent: str
    action: str
    result: str
    confidence: float
    # Supplementary fields
    transcription: str = ""
    transcript_summary: str = ""
    detected_objects: list[str] = Field(default_factory=list)
    frame_text: list[str] = Field(default_factory=list)
    language: str = "unknown"
    duration: float = 0.0
    objects: list[str] = Field(default_factory=list)
    note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)