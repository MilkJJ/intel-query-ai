"""
Intent classification for the OrchestratorAgent.

Maps user queries to (agent, action, confidence) tuples using keyword rules.
Rules are evaluated top-to-bottom; the first match wins.

Design note: this module is intentionally self-contained with no external
dependencies so it can be replaced with an LLM-based classifier or an MCP
tool in the future without touching any other agent code.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Intent:
    agent: str
    action: str
    confidence: float


# Each rule: (keywords, agent_name, action, base_confidence)
# Rules are checked in order; more specific rules must come before broader ones.
_INTENT_RULES: list[tuple[list[str], str, str, float]] = [
    # ── Report agent ─────────────────────────────────────────────────────────
    (
        ["powerpoint", "ppt", "presentation", "slides", "slide deck"],
        "report", "generate_ppt", 0.97,
    ),
    (
        ["generate pdf", "create pdf", "export pdf", "pdf report", "pdf document"],
        "report", "generate_pdf", 0.97,
    ),
    (
        ["pdf", "report", "generate report", "create report", "export report"],
        "report", "generate_pdf", 0.93,
    ),

    # ── Vision agent ─────────────────────────────────────────────────────────
    (
        ["graph", "chart", "diagram", "plot", "bar chart", "pie chart", "line graph"],
        "vision", "detect_charts_and_graphs", 0.95,
    ),
    (
        ["extract text", "read text", "text in frame", "text on screen", "ocr", "written text"],
        "vision", "extract_text_from_frames", 0.94,
    ),
    (
        [
            "what object",
            "what's object",
            "what objects",
            "detect object",
            "detect objects",
            "object is in",
            "objects shown",
            "objects in",
            "identify object",
            "identify objects",
            "object in the video",
            "objects in the video",
            "what is in the video",
        ],
        "vision", "detect_objects", 0.93,
    ),
    (
        ["vision", "frame", "scene", "visual", "analyze video", "what is shown",
         "what do you see", "look at", "describe"],
        "vision", "analyze_frames", 0.90,
    ),

    # ── Transcription agent ───────────────────────────────────────────────────
    (
        ["summar", "overview", "brief", "tldr", "tl;dr", "key points",
         "main points", "highlights", "recap"],
        "transcription", "summarize_transcript", 0.95,
    ),
    (
        ["transcribe", "transcript", "caption", "subtitles", "words spoken",
         "what was said", "what did they say"],
        "transcription", "get_transcript", 0.97,
    ),

    # ── Fallback ──────────────────────────────────────────────────────────────
    # Empty keyword list = always matches; placed last as catch-all.
    ([], "transcription", "answer_query", 0.55),
]


def classify_intent(query: str) -> Intent:
    """
    Classify a user query into an (agent, action, confidence) intent.

    Confidence is boosted slightly when multiple keywords from the same rule
    match the query, capped at 0.99.
    """
    normalized = query.lower().strip()

    for keywords, agent, action, base_confidence in _INTENT_RULES:
        if not keywords:
            return Intent(agent=agent, action=action, confidence=base_confidence)

        matches = sum(1 for kw in keywords if kw in normalized)
        if matches:
            boosted = min(0.99, base_confidence + (matches - 1) * 0.01)
            return Intent(agent=agent, action=action, confidence=boosted)

    # Should be unreachable due to the catch-all rule
    return Intent(agent="transcription", action="get_transcript", confidence=0.50)
