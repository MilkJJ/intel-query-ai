from agents.base import BaseAgent
from agents.context import AgentContext
from agents.result import AgentResult
from agents.transcription_agent import TranscriptionAgent


class GenerationAgent(BaseAgent):
    name = "generation"

    def __init__(self, transcription_agent: TranscriptionAgent):
        self.transcription_agent = transcription_agent

    def can_handle(self, query: str) -> bool:
        return True

    def run(self, context: AgentContext) -> AgentResult:
        query = context.query
        transcription_payload = self.transcription_agent.run(context)
        transcript_text = transcription_payload.transcription

        if not transcript_text:
            response = "I could not find spoken content to answer from."
        elif "summary" in query.lower() or "summar" in query.lower():
            response = f"Summary based on the transcript: {transcript_text[:400]}"
        else:
            response = (
                f"Generation agent used the transcript to answer your request: '{query}'.\n\n"
                f"Transcript context:\n{transcript_text[:1200]}"
            )

        return AgentResult(
            agent=self.name,
            response=response,
            transcription=transcript_text,
            language=transcription_payload.language,
            duration=transcription_payload.duration,
        )