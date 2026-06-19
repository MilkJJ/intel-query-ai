import { useState } from "react";

const QUERY_SUGGESTIONS = [
  {
    category: "Transcription",
    queries: [
      { text: "Transcribe the video", icon: "📝" },
      { text: "Get the full transcript", icon: "📄" },
    ],
  },
  {
    category: "Vision",
    queries: [
      { text: "What objects are shown?", icon: "👁️" },
      { text: "Are there any graphs?", icon: "📊" },
      { text: "What text appears on screen?", icon: "🔤" },
    ],
  },
  {
    category: "Generation",
    queries: [
      { text: "Summarize this video", icon: "📌" },
      { text: "What are the key topics?", icon: "🎯" },
    ],
  },
  {
    category: "Reports",
    queries: [
      { text: "Generate a PDF report", icon: "📄" },
      { text: "Create a PowerPoint presentation", icon: "📑" },
    ],
  },
  {
    category: "Complete Analysis",
    queries: [
      { text: "Analyze the video completely", icon: "🔬" },
      { text: "Give me all insights", icon: "💡" },
    ],
  },
];

export default function ChatBox({ onSend, onFileSelect, selectedFileName }) {
  const [input, setInput] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);

  const handleSend = () => {
    if (!input.trim()) return;

    onSend(input);
    setInput("");
    setShowSuggestions(false);
  };

  const handleSuggestionClick = (suggestion) => {
    onSend(suggestion);
    setInput("");
    setShowSuggestions(false);
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = (event) => {
    const selectedFile = event.target.files?.[0] ?? null;
    onFileSelect?.(selectedFile);
    event.target.value = "";
  };

  return (
    <div style={{ padding: "12px 16px", borderTop: "1px solid #333", background: "#181818" }}>
      {selectedFileName && (
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            marginBottom: "10px",
            padding: "6px 10px",
            borderRadius: "999px",
            background: "#23263b",
            color: "#d9ddff",
            fontSize: "13px",
          }}
        >
          <span>Video</span>
          <span>{selectedFileName}</span>
        </div>
      )}

      {/* Query Suggestions */}
      {showSuggestions && selectedFileName && (
        <div
          style={{
            marginBottom: "12px",
            padding: "12px",
            borderRadius: "8px",
            background: "#202020",
            border: "1px solid #333",
          }}
        >
          <div style={{ fontSize: "12px", color: "#999", marginBottom: "8px", fontWeight: "500" }}>
            Suggested queries:
          </div>
          {QUERY_SUGGESTIONS.map((category) => (
            <div key={category.category} style={{ marginBottom: "8px" }}>
              <div style={{ fontSize: "11px", color: "#666", marginBottom: "4px" }}>
                {category.category}
              </div>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "6px",
                }}
              >
                {category.queries.map((query) => (
                  <button
                    key={query.text}
                    onClick={() => handleSuggestionClick(query.text)}
                    style={{
                      padding: "6px 10px",
                      borderRadius: "6px",
                      border: "1px solid #464feb",
                      background: "#1a1a2e",
                      color: "#cbd5e1",
                      cursor: "pointer",
                      fontSize: "12px",
                      whiteSpace: "nowrap",
                      transition: "all 0.2s",
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.background = "#464feb";
                      e.target.style.color = "#fff";
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.background = "#1a1a2e";
                      e.target.style.color = "#cbd5e1";
                    }}
                  >
                    <span style={{ marginRight: "4px" }}>{query.icon}</span>
                    {query.text}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <label
          htmlFor="chat-video-upload"
          style={{
            width: "42px",
            height: "42px",
            borderRadius: "10px",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            background: "#252525",
            border: "1px solid #383838",
            cursor: "pointer",
            fontSize: "18px",
          }}
          title="Upload video"
        >
          📎
        </label>
        <input
          id="chat-video-upload"
          type="file"
          accept=".mp4,.avi,.mov,.mkv,.flv,.wmv"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />
        <input
          style={{
            flex: 1,
            padding: "12px 14px",
            borderRadius: "12px",
            border: "1px solid #3a3a3a",
            background: "#232323",
            color: "#fff",
          }}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => selectedFileName && setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 100)}
          placeholder="Ask something about the video..."
        />
        <button
          onClick={handleSend}
          style={{
            padding: "12px 16px",
            borderRadius: "12px",
            border: "none",
            background: "#464feb",
            color: "#fff",
            cursor: "pointer",
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}