import { useState, type ChangeEvent, type KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (text: string) => void;
}

export default function ChatInput({ onSend }: ChatInputProps) {
  const [text, setText] = useState("");
  const canSend = text.trim().length > 0;

  const handleSend = () => {
    if (!canSend) return;
    onSend(text);
    setText(""); // Clear after a successful send.
  };

  const handleChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    setText(event.target.value);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends; Shift+Enter inserts a newline.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  // Note: deliberately not an HTML <form> — the button and key handler are
  // wired directly so there is no native submission.
  return (
    <div className="chat-input">
      <textarea
        className="chat-input__textarea"
        value={text}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="Type a question…"
        aria-label="Message"
        rows={3}
      />
      <button
        type="button"
        className="button button--primary chat-input__send"
        onClick={handleSend}
        disabled={!canSend}
      >
        Send
      </button>
    </div>
  );
}
