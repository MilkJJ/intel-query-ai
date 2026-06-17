export default function MessageItem({ message }) {
  const isUser = message.role === "user";

  return (
    <div
      style={{
        textAlign: isUser ? "right" : "left",
        margin: "10px 0",
      }}
    >
      <div
        style={{
          display: "inline-block",
          padding: "10px",
          background: isUser ? "#007bff" : "#333",
          borderRadius: "10px",
          maxWidth: "70%",
        }}
      >
        {message.content}
      </div>
    </div>
  );
}