from pydantic import BaseModel


class ExportRequest(BaseModel):
    format: str
    title: str = "Video AI Report"
    filename: str | None = None
    query: str
    agent: str
    response: str
    transcription: str = ""
    language: str = "unknown"
    duration: float = 0


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
    language: str = "unknown"
    duration: float = 0.0
    objects: list[str] = []
    note: str | None = None