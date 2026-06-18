import { useEffect, useRef } from "react";
import MessageItem from "./MessageItem";

export default function MessageList({ messages, onExportPdf, onExportPpt }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "10px" }}>
      {messages.map((msg, index) => (
        <MessageItem
          key={index}
          message={msg}
          onExportPdf={onExportPdf}
          onExportPpt={onExportPpt}
        />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}