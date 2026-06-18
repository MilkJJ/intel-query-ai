export default function MessageItem({ message, onExportPdf, onExportPpt }) {
  const isUser = message.role === "user";
  const isThinking = Boolean(message.isThinking);
  const canExport = message.export?.canExport ?? false;

  return (
    <div
      style={{
        textAlign: isUser ? "right" : "left",
        margin: "10px 0",
      }}
    >
      <div
        style={{
          display: "inline-flex",
          flexDirection: "column",
          gap: "10px",
          padding: "10px",
          background: isUser ? "#007bff" : isThinking ? "#2a2f3a" : "#333",
          borderRadius: "10px",
          maxWidth: "70%",
          color: "#fff",
          opacity: isThinking ? 0.95 : 1,
        }}
      >
        <div
          style={{
            whiteSpace: "pre-wrap",
            lineHeight: 1.5,
            fontStyle: isThinking ? "italic" : "normal",
            color: isThinking ? "#cbd5e1" : "#fff",
          }}
        >
          {message.content}
          {isThinking && <span aria-hidden="true">...</span>}
        </div>
        {!isUser && canExport && (
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button
              onClick={() => {
                if (message.export?.format === "ppt") {
                  onExportPpt?.(message.export);
                  return;
                }
                onExportPdf?.(message.export);
              }}
              style={{
                padding: "8px 10px",
                borderRadius: "8px",
                border: "1px solid #4b5563",
                background: "#111827",
                color: "#f9fafb",
                cursor: "pointer",
                fontSize: "12px",
              }}
            >
              {message.export?.format === "ppt" ? "Download PPT" : "Download PDF"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}