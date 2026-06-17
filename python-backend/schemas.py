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