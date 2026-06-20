import { useCallback, useState } from "react";
import Header from "./components/Header";
import Dashboard from "./components/Dashboard";
import ChatDrawer from "./components/chat/ChatDrawer";
import { PLACEHOLDER_ASSISTANT_REPLY } from "./stubs";
import type { Message } from "./types";

/**
 * App shell and the only state owner in this skeleton.
 *
 * State:
 *  - isChatOpen: drawer visibility (default closed)
 *  - messages:   local-only chat history (default empty)
 */
export default function App() {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);

  const toggleChat = useCallback(() => setIsChatOpen((open) => !open), []);
  const closeChat = useCallback(() => setIsChatOpen(false), []);

  const handleSendMessage = useCallback((text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      createdAt: Date.now(),
    };

    // Local-only stub: append the user message, then a fixed placeholder reply.
    // No network calls, no timers required.
    // TODO: replace the placeholder reply with a real POST /query call to the backend.
    const assistantMessage: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: PLACEHOLDER_ASSISTANT_REPLY,
      createdAt: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
  }, []);

  return (
    <div className="app-shell">
      <Header isChatOpen={isChatOpen} onToggleChat={toggleChat} />
      <main className="app-main">
        <Dashboard />
      </main>
      <ChatDrawer
        isOpen={isChatOpen}
        onClose={closeChat}
        messages={messages}
        onSend={handleSendMessage}
      />
    </div>
  );
}
