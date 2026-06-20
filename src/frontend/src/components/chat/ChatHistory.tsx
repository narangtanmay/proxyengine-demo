import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import type { Message } from "../../types";

interface ChatHistoryProps {
  messages: Message[];
}

export default function ChatHistory({ messages }: ChatHistoryProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the newest message whenever the history changes.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="chat-history chat-history--empty">
        <p className="chat-history__empty-text">Ask a question to get started.</p>
      </div>
    );
  }

  return (
    <div className="chat-history" role="log" aria-live="polite">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
