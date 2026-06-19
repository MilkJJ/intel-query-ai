import { useEffect, useState } from "react";
import MessageList from "../components/Chat/MessageList";
import ChatBox from "../components/Chat/ChatBox";
import MainLayout from "../components/Layout/MainLayout";

const CHAT_HISTORY_STORAGE_KEY = "chatHistory";

function generateLocalMessageId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function normalizeStoredMessages(messages) {
  if (!Array.isArray(messages)) {
    return [];
  }

  return messages.map((message) => ({
    ...message,
    id: message?.id || generateLocalMessageId(),
  }));
}

function loadStoredMessages() {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const storedMessages = window.localStorage.getItem(CHAT_HISTORY_STORAGE_KEY);

    if (!storedMessages) {
      return [];
    }

    const parsedMessages = JSON.parse(storedMessages);
    return normalizeStoredMessages(parsedMessages);
  } catch {
    return [];
  }
}

export default function Home() {
  const [messages, setMessages] = useState(loadStoredMessages);
  const [videoFile, setVideoFile] = useState(null);
  const [activeHistoryMessageId, setActiveHistoryMessageId] = useState(null);

  const createMessageId = () =>
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

  useEffect(() => {
    window.localStorage.setItem(CHAT_HISTORY_STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  const chatHistory = messages
    .filter((message) => message.role === "user")
    .map((message, index) => ({
      id: message.id,
      label: `Prompt ${index + 1}`,
      text: message.content,
    }))
    .reverse();

  const handleHistorySelect = (historyItem) => {
    if (!historyItem?.id) {
      return;
    }

    setActiveHistoryMessageId(historyItem.id);
  };

  const handleFileSelect = (file) => {
    setVideoFile(file);
  };

  const handleClearHistory = () => {
    setMessages([]);
    setActiveHistoryMessageId(null);

    if (typeof window !== "undefined") {
      window.localStorage.removeItem(CHAT_HISTORY_STORAGE_KEY);
    }
  };

  const downloadExport = async (format, exportPayload) => {
    if (!exportPayload) {
      return;
    }

    try {
      const response = await fetch("http://localhost:8000/export", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          format,
          title: "Video Analysis and Insights Report",
          filename: videoFile?.name,
          query: exportPayload.query,
          agent: exportPayload.agent,
          response: exportPayload.response,
          transcription: exportPayload.transcription || "",
          transcript_summary: exportPayload.transcript_summary || "",
          detected_objects: exportPayload.detected_objects || [],
          frame_text: exportPayload.frame_text || [],
          language: exportPayload.language || "unknown",
          duration: exportPayload.duration || 0,
          // Phase 5: Include LLM insights and enhanced metadata
          llm_insights: exportPayload.llm_insights || {},
          metadata: exportPayload.metadata || {},
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Export failed with status ${response.status}`);
      }

      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      const extension = format === "ppt" ? "pptx" : "pdf";

      link.href = blobUrl;
      link.download = `${(videoFile?.name || "video-ai-output").replace(/\.[^.]+$/, "")}.${extension}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Export failed: ${error.message}`,
        },
      ]);
    }
  };

  const handleSend = async (text) => {
    if (!videoFile) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "📹 Please upload a video first to get started. Click the attachment button (📎) to select an MP4, MOV, AVI, MKV, FLV, or WMV file.\n\nOnce uploaded, try asking:\n• 'Transcribe the video' - Get the full transcript\n• 'What objects are shown?' - Detect objects in the video\n• 'Summarize this video' - Get a brief summary\n• 'Generate a PDF report' - Create an insight-driven report",
        },
      ]);
      return;
    }

    const userMessage = { id: createMessageId(), role: "user", content: text };
    const pendingMessageId = createMessageId();
    setActiveHistoryMessageId(userMessage.id);
    setMessages((prev) => [...prev, userMessage]);
    setMessages((prev) => [
      ...prev,
      {
        id: pendingMessageId,
        role: "assistant",
        content: "Analyzing your video",
        isThinking: true,
      },
    ]);

    try {
      const formData = new FormData();
      formData.append("file", videoFile);
      formData.append("query", text);

      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => null);
        throw new Error(errorData?.detail || `Request failed with status ${res.status}`);
      }

      const data = await res.json();
      const exportable = data.action === "generate_pdf" || data.action === "generate_ppt";
      const assistantMessage = {
        id: pendingMessageId,
        role: "assistant",
        content: `[${data.agent ?? "assistant"}] ${data.result ?? "No response returned."}`,
        export: exportable
          ? {
              canExport: true,
              format: data.action === "generate_pdf" ? "pdf" : "ppt",
              query: data.query,
              agent: data.agent,
              response: data.result,
              transcription: data.transcription || "",
              transcript_summary: data.transcript_summary || "",
              detected_objects: data.detected_objects || [],
              frame_text: data.frame_text || [],
              language: data.language || "unknown",
              duration: data.duration || 0,
              // Phase 5: Enhanced metadata with LLM insights
              llm_insights: data.llm_insights || {},
              metadata: data.metadata || {},
            }
          : null,
      };

      setMessages((prev) => [
        ...prev.map((message) => (message.id === pendingMessageId ? assistantMessage : message)),
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev.map((message) =>
          message.id === pendingMessageId
            ? {
                id: pendingMessageId,
                role: "assistant",
                content: `⚠️ Request failed: ${error.message}\n\nMake sure the backend is running on http://localhost:8000`,
              }
            : message,
        ),
      ]);
    }
  };

  return (
    <MainLayout
      history={chatHistory}
      activeVideoName={videoFile?.name}
      onClearHistory={handleClearHistory}
      onSelectHistoryItem={handleHistorySelect}
      activeHistoryId={activeHistoryMessageId}
    >
      <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <MessageList
          messages={messages}
          onExportPdf={(exportPayload) => downloadExport("pdf", exportPayload)}
          onExportPpt={(exportPayload) => downloadExport("ppt", exportPayload)}
          scrollToMessageId={activeHistoryMessageId}
        />
        <ChatBox
          onSend={handleSend}
          onFileSelect={handleFileSelect}
          selectedFileName={videoFile?.name}
        />
      </div>
    </MainLayout>
  );
}