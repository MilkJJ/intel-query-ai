import { useEffect, useState } from "react";
import MessageList from "../components/Chat/MessageList";
import ChatBox from "../components/Chat/ChatBox";
import MainLayout from "../components/Layout/MainLayout";

const CHAT_HISTORY_STORAGE_KEY = "chatHistory";

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
    return Array.isArray(parsedMessages) ? parsedMessages : [];
  } catch {
    return [];
  }
}

export default function Home() {
  const [messages, setMessages] = useState(loadStoredMessages);
  const [videoFile, setVideoFile] = useState(null);
  const [lastResult, setLastResult] = useState(null);

  useEffect(() => {
    window.localStorage.setItem(CHAT_HISTORY_STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  const chatHistory = messages
    .filter((message) => message.role === "user")
    .map((message, index) => ({
      id: `${index}-${message.content}`,
      label: `Prompt ${index + 1}`,
      text: message.content,
    }))
    .reverse();

  const handleFileSelect = (file) => {
    setVideoFile(file);
  };

  const handleClearHistory = () => {
    setMessages([]);
    setLastResult(null);

    if (typeof window !== "undefined") {
      window.localStorage.removeItem(CHAT_HISTORY_STORAGE_KEY);
    }
  };

  const downloadExport = async (format) => {
    if (!lastResult) {
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
          title: "Video AI Output",
          filename: videoFile?.name,
          query: lastResult.query,
          agent: lastResult.agent,
          response: lastResult.response,
          transcription: lastResult.transcription || "",
          language: lastResult.language || "unknown",
          duration: lastResult.duration || 0,
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
          content: "Please upload a video first, then send a query like 'Transcribe the video'.",
        },
      ]);
      return;
    }

    const userMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);

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
      setLastResult(data);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `[${data.agent ?? "assistant"}] ${data.response ?? "No response returned."}`,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Request failed: ${error.message}`,
        },
      ]);
    }
  };

  return (
    <MainLayout
      history={chatHistory}
      activeVideoName={videoFile?.name}
      onClearHistory={handleClearHistory}
      onExportPdf={() => downloadExport("pdf")}
      onExportPpt={() => downloadExport("ppt")}
      canExport={Boolean(lastResult)}
    >
      <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <MessageList messages={messages} />
        <ChatBox
          onSend={handleSend}
          onFileSelect={handleFileSelect}
          selectedFileName={videoFile?.name}
        />
      </div>
    </MainLayout>
  );
}