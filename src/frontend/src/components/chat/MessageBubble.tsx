import type { Message } from "../../types";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  return (
    <div className={`message-bubble message-bubble--${isUser ? "user" : "assistant"}`}>
      {/* Plain text only — no markdown rendering in this pass. */}
      <p className="message-bubble__content">{message.content}</p>
    </div>
  );
}
