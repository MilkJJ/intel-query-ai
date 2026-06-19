export default function Sidebar({
  history = [],
  activeVideoName,
  onClearHistory,
  onSelectHistoryItem,
  activeHistoryId,
}) {
  const handleClearClick = () => {
    const confirmed = window.confirm("Clear the chat history? This will remove all messages from the current session.");
    if (!confirmed) {
      return;
    }

    onClearHistory?.();
  };

  return (
    <div
      style={{
        width: "280px",
        background: "#111",
        padding: "18px 14px",
        borderRight: "1px solid #333",
        color: "#fff",
        display: "flex",
        flexDirection: "column",
        gap: "14px",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "10px" }}>
        <div>
          <h3 style={{ margin: "0 0 6px 0", fontSize: "18px" }}>Intel Query AI</h3>
          <p style={{ margin: 0, fontSize: "12px", color: "#9ca3af", lineHeight: 1.5 }}>
            Upload a video and prompt your queries.
          </p>
        </div>
        <button
          onClick={handleClearClick}
          disabled={history.length === 0}
          style={{
            padding: "8px 10px",
            borderRadius: "8px",
            border: "1px solid #303030",
            background: history.length === 0 ? "#1a1a1a" : "#202020",
            color: history.length === 0 ? "#5f6368" : "#f3f4f6",
            cursor: history.length === 0 ? "not-allowed" : "pointer",
            fontSize: "12px",
          }}
        >
          Clear
        </button>
      </div>

      <div
        style={{
          padding: "12px",
          borderRadius: "10px",
          background: "#1a1a1a",
          border: "1px solid #2f2f2f",
        }}
      >
        <div style={{ fontSize: "11px", textTransform: "uppercase", color: "#8b93a7", marginBottom: "6px" }}>
          Active video
        </div>
        <div style={{ fontSize: "13px", lineHeight: 1.5, wordBreak: "break-word" }}>
          {activeVideoName || "No video selected"}
        </div>
      </div>

      <div style={{ minHeight: 0, display: "flex", flexDirection: "column", flex: 1 }}>
        <div style={{ fontSize: "11px", textTransform: "uppercase", color: "#8b93a7", marginBottom: "10px" }}>
          Chat history
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px", overflowY: "auto", paddingRight: "4px" }}>
          {history.length === 0 ? (
            <div
              style={{
                padding: "12px",
                borderRadius: "10px",
                background: "#171717",
                color: "#8b93a7",
                fontSize: "13px",
                lineHeight: 1.5,
              }}
            >
              Start a conversation after uploading a video.
            </div>
          ) : (
            history.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectHistoryItem?.(item)}
                style={{
                  textAlign: "left",
                  width: "100%",
                  padding: "12px",
                  borderRadius: "10px",
                  background: item.id === activeHistoryId ? "#1e293b" : "#171717",
                  border: item.id === activeHistoryId ? "1px solid #334155" : "1px solid #282828",
                  cursor: "pointer",
                  color: "inherit",
                }}
              >
                <div style={{ fontSize: "11px", color: "#7d86a0", marginBottom: "6px" }}>{item.label}</div>
                <div style={{ fontSize: "13px", lineHeight: 1.5, color: "#f5f5f5" }}>{item.text}</div>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}