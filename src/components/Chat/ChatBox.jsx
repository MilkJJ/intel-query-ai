import { useState } from "react";

export default function ChatBox({ onSend, onFileSelect, selectedFileName }) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;

    onSend(input);
    setInput("");
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