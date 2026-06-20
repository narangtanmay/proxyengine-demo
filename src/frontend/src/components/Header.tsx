import CompanyPicker from "./CompanyPicker";

interface HeaderProps {
  isChatOpen: boolean;
  onToggleChat: () => void;
}

export default function Header({ isChatOpen, onToggleChat }: HeaderProps) {
  return (
    <header className="app-header">
      <h1 className="app-title">Compensation advisor</h1>

      <div className="app-header__controls">
        <CompanyPicker />

        {/* When the drawer is open the close action lives inside the drawer
            header, so this toggle simply hides to avoid a duplicate control. */}
        {!isChatOpen && (
          <button
            type="button"
            className="button button--primary"
            onClick={onToggleChat}
            aria-haspopup="dialog"
            aria-expanded={isChatOpen}
          >
            Chat
          </button>
        )}
      </div>
    </header>
  );
}
