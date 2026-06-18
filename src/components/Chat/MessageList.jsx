import MessageItem from "./MessageItem";

export default function MessageList({ messages, onExportPdf, onExportPpt }) {
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
    </div>
  );
}