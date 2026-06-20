import { useEffect, useRef } from "react";
import ChatHeader from "./ChatHeader";
import ChatHistory from "./ChatHistory";
import ChatInput from "./ChatInput";
import type { Message } from "../../types";

interface ChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  messages: Message[];
  onSend: (text: string) => void;
}

export default function ChatDrawer({ isOpen, onClose, messages, onSend }: ChatDrawerProps) {
  const drawerRef = useRef<HTMLElement>(null);

  // Move focus into the drawer when it opens for keyboard accessibility.
  useEffect(() => {
    if (isOpen) {
      drawerRef.current?.focus();
    }
  }, [isOpen]);

  // Escape closes the drawer while it is open.
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <aside
      ref={drawerRef}
      className={`chat-drawer${isOpen ? " chat-drawer--open" : ""}`}
      role="dialog"
      aria-label="Chat"
      // When closed the drawer is visually hidden via CSS `visibility: hidden`,
      // which also removes its controls from the tab order.
      aria-hidden={!isOpen}
      tabIndex={-1}
    >
      <ChatHeader onClose={onClose} />
      <ChatHistory messages={messages} />
      <ChatInput onSend={onSend} />
    </aside>
  );
}
