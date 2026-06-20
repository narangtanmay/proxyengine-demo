interface ChatHeaderProps {
  onClose: () => void;
}

export default function ChatHeader({ onClose }: ChatHeaderProps) {
  return (
    <div className="chat-header">
      <h2 className="chat-header__title">Ask about this company</h2>
      <button
        type="button"
        className="button button--icon"
        onClick={onClose}
        aria-label="Close chat"
      >
        <span aria-hidden="true">✕</span>
      </button>
    </div>
  );
}
