import { useEffect, useRef } from "react";
import MessageItem from "./MessageItem";

export default function MessageList({ messages, onExportPdf, onExportPpt, scrollToMessageId }) {
  const bottomRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  useEffect(() => {
    if (!scrollToMessageId || !containerRef.current) {
      return;
    }

    const target = containerRef.current.querySelector(`[data-message-id="${scrollToMessageId}"]`);
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [scrollToMessageId]);

  return (
    <div ref={containerRef} style={{ flex: 1, overflowY: "auto", padding: "10px" }}>
      {messages.map((msg, index) => (
        <div key={msg.id || index} data-message-id={msg.id || ""}>
          <MessageItem
            message={msg}
            onExportPdf={onExportPdf}
            onExportPpt={onExportPpt}
          />
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}