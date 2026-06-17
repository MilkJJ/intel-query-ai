import MessageItem from "./MessageItem";

export default function MessageList({ messages }) {
  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "10px" }}>
      {messages.map((msg, index) => (
        <MessageItem key={index} message={msg} />
      ))}
    </div>
  );
}