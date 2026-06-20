# Frontend skeleton specification

> **Purpose for the agent:** Build a non-functional UI skeleton for an executive-compensation
> benchmarking tool. This pass is about *structure and placeholders only*. There is **no backend
> and no LLM yet** — every data source and every send action is stubbed. The goal is a clickable
> shell with the right regions in the right places and clean seams where real data will plug in
> later.

---

## 1. Context

The eventual product lets a user inspect one company's executive pay, see how it compares to peers,
and ask a language model questions about it in natural language. Two surfaces:

- A **dashboard** (the main area) that will later show peer comparisons, pay breakdowns, and flags.
- A **chat panel** (a side drawer) where the user will later converse with an LLM about the company.

For this skeleton, both surfaces exist visually but are wired to local placeholder state only.

---

## 2. Scope

**In scope (build this):**

- App shell with a header and a main content area.
- A dashboard region rendered as labelled empty placeholders (no real charts or data).
- A right-side chat drawer that can be opened and closed via a toggle control.
- Inside the drawer: a scrollable message history, a multi-line text input, and a send button.
- Local-only chat behavior: sending appends the typed message to the history and appends a clearly
  marked placeholder "assistant" reply. No network calls.
- A quality floor: responsive layout, keyboard accessibility, sensible empty states.

**Out of scope (do NOT build):**

- Any API calls, data fetching, or backend integration.
- Any real LLM connection or streaming.
- Real charts, real company data, or a working company picker (a static stub is fine).
- Authentication, routing to multiple pages, persistence, or global state libraries.
- Visual design polish, theming systems, or animation beyond a basic drawer open/close.

Mark every future integration point with a `// TODO:` comment so the seams are obvious.

---

## 3. Tech stack

- **React + TypeScript**, scaffolded with **Vite**.
- Function components and hooks only. No class components.
- Local component state with `useState` / `useReducer`. **No** Redux, Zustand, or context-based
  global stores in this pass.
- Plain CSS modules or a single global stylesheet. Tailwind is acceptable if already familiar, but
  not required — do not add a styling framework just for this.
- Charting library (e.g. Recharts) may be listed as a future dependency but **must not** be used or
  imported yet.

---

## 4. Layout overview

When the chat drawer is **closed**, the dashboard fills the width. When **open**, the drawer occupies
a fixed-width column on the right as an overlay; the dashboard stays mounted underneath.

```
 closed:                                 open:
┌──────────────────────────────────────┐  ┌───────────────────────────┬──────────────┐
│  header        [company ▾]   [ Chat ] │  │ header     [company ▾] [✕]│  Chat        │
├──────────────────────────────────────┤  ├───────────────────────────┤  ┌────────┐  │
│                                      │  │                           │  │ history│  │
│   dashboard placeholder region       │  │   dashboard (unchanged)   │  │ scrolls│  │
│   ┌────────┐ ┌────────┐ ┌────────┐   │  │                           │  │        │  │
│   │ card   │ │ card   │ │ card   │   │  │                           │  └────────┘  │
│   └────────┘ └────────┘ └────────┘   │  │                           │  [textarea ] │
│                                      │  │                           │  [   Send  ] │
└──────────────────────────────────────┘  └───────────────────────────┴──────────────┘
```

Suggested drawer width: ~380–420px on desktop. On narrow viewports (< 640px) the drawer becomes a
full-width overlay.

---

## 5. Files to create

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── src/
    ├── main.tsx                 # React entry point
    ├── App.tsx                  # app shell: header + dashboard + chat drawer
    ├── types.ts                 # shared types (Message, Company)
    ├── stubs.ts                 # placeholder data + the fake assistant reply
    ├── components/
    │   ├── Header.tsx           # title, company picker stub, chat toggle button
    │   ├── CompanyPicker.tsx    # static <select> stub, non-functional
    │   ├── Dashboard.tsx        # placeholder region with empty cards
    │   ├── PlaceholderCard.tsx  # a single labelled empty card
    │   └── chat/
    │       ├── ChatDrawer.tsx   # the openable side panel container
    │       ├── ChatHeader.tsx   # drawer title + close button
    │       ├── ChatHistory.tsx  # scrollable list of messages
    │       ├── MessageBubble.tsx# one message (user vs assistant styling)
    │       └── ChatInput.tsx    # textarea + send button
    └── styles/
        └── (CSS files as needed)
```

Keep components small and single-purpose. Do not put business logic in presentational components.

---

## 6. Component specifications

### 6.1 `App.tsx` — shell and state owner

Owns the only state in the app:

- `isChatOpen: boolean` — drawer visibility, default `false`.
- `messages: Message[]` — chat history, default `[]`.

Renders `Header`, `Dashboard`, and `ChatDrawer`. Passes `isChatOpen` and an `onToggleChat` handler to
`Header` and `ChatDrawer`. Passes `messages` and a `onSendMessage(text: string)` handler down to the
chat subtree.

Implements `onSendMessage` (see §7) and the open/close toggle.

### 6.2 `Header.tsx`

- App title on the left (e.g. "Compensation advisor" — sentence case).
- `CompanyPicker` in the middle or right.
- A button labelled **Chat** that toggles the drawer. When the drawer is open, this button may be
  hidden or relabelled; the close action also lives inside the drawer header.
- The toggle button must have an accessible label and be reachable by keyboard.

### 6.3 `CompanyPicker.tsx`

- A static `<select>` populated from a hardcoded list in `stubs.ts` (3–4 fake company names).
- Selecting an option does nothing functional yet. Add `// TODO: drive dashboard + chat context from
  selected company`.

### 6.4 `Dashboard.tsx`

- A responsive grid (CSS grid or flex-wrap) of `PlaceholderCard`s.
- Render 4–6 cards with descriptive titles that signal future content, e.g.:
  - "Pay vs. peers"
  - "Compensation breakdown"
  - "Pay-for-performance"
  - "Red flags"
  - "Company overview"
- No charts, no numbers. Each card shows its title and a muted "Coming soon" / "No data yet" body.
- Add `// TODO: fetch GET /company/{id}/dashboard and render real content`.

### 6.5 `PlaceholderCard.tsx`

- Props: `{ title: string; children?: React.ReactNode }`.
- A bordered container with the title at top and an empty/placeholder body. Generic and reusable.

### 6.6 `chat/ChatDrawer.tsx`

- Props: `{ isOpen: boolean; onClose: () => void; messages: Message[]; onSend: (text: string) => void }`.
- When `isOpen` is false it is hidden (and not focus-reachable). When true it slides/appears on the
  right.
- Contains, top to bottom: `ChatHeader`, `ChatHistory` (flex-grow, scrollable), `ChatInput` (pinned to
  the bottom of the drawer).
- A basic open/close transition is fine; respect `prefers-reduced-motion`.
- `Escape` key closes the drawer.

### 6.7 `chat/ChatHeader.tsx`

- Drawer title (e.g. "Ask about this company") and a close button (✕) calling `onClose`.
- Close button needs an accessible label.

### 6.8 `chat/ChatHistory.tsx`

- Props: `{ messages: Message[] }`.
- Renders a `MessageBubble` per message in order.
- **Empty state:** when there are no messages, show an inviting placeholder, e.g. "Ask a question to
  get started." — a real instruction, not lorem ipsum.
- Auto-scroll to the newest message when `messages` changes (scroll the container to the bottom).

### 6.9 `chat/MessageBubble.tsx`

- Props: `{ message: Message }`.
- User messages and assistant messages are visually distinct (e.g. alignment and/or background).
- Render `message.content` as plain text. No markdown rendering required in this pass.

### 6.10 `chat/ChatInput.tsx`

- Props: `{ onSend: (text: string) => void }`.
- A multi-line `<textarea>` and a **Send** button.
- Send is triggered by clicking the button **or** pressing `Enter` (use `Shift+Enter` for a newline).
- Trim input; ignore empty/whitespace-only sends. Clear the textarea after a successful send.
- Disable the Send button when the input is empty.
- **Do not** use an HTML `<form>` element with native submission — wire the button and key handler
  directly.

---

## 7. Stubbed send behavior (the only "logic" in this pass)

`onSendMessage(text)` in `App.tsx` must:

1. Append a `Message` with `role: "user"` and the trimmed `text` to `messages`.
2. Append a second `Message` with `role: "assistant"` whose content is a fixed placeholder from
   `stubs.ts`, e.g. **"The assistant isn't connected yet — this is a placeholder reply."**
3. Do **nothing** else. No fetch, no timers required (an optional ~400ms delay before the placeholder
   reply is acceptable for realism, but keep it trivial to remove).

Mark this clearly:

```ts
// TODO: replace the placeholder reply with a real POST /query call to the backend.
```

This keeps the full chat loop (type → send → history updates → scroll) demonstrable with zero
dependencies.

---

## 8. Types (`types.ts`)

```ts
export type Role = "user" | "assistant";

export interface Message {
  id: string;          // any unique id, e.g. crypto.randomUUID()
  role: Role;
  content: string;
  createdAt: number;   // Date.now()
}

export interface Company {
  id: string;
  name: string;
}
```

`stubs.ts` exports a small `Company[]` and the placeholder reply string.

---

## 9. Quality floor (non-negotiable, cheap to meet)

- **Responsive:** usable from ~360px wide up to desktop. Drawer goes full-width on small screens.
- **Keyboard:** drawer toggle, close button, textarea, and send button are all keyboard-operable with
  visible focus styles. `Escape` closes the drawer; focus moves into the drawer when it opens.
- **Reduced motion:** wrap any open/close transition in `@media (prefers-reduced-motion: no-preference)`.
- **Copy:** sentence case everywhere. Button labels say what happens ("Send", "Chat", "Close").
  Empty states are instructions, not mood text.
- **No console errors or warnings** on load or on send.

Visual styling can be plain and neutral — clean spacing, a single accent, legible type. Do not invest
in a distinctive visual identity in this pass; that comes later.

---

## 10. Acceptance criteria

The skeleton is done when all of the following are true:

- [ ] `npm install && npm run dev` starts the app with no errors.
- [ ] The header shows a title, a (non-functional) company picker, and a chat toggle.
- [ ] The dashboard area shows 4–6 labelled placeholder cards in a responsive grid.
- [ ] Clicking the toggle opens a right-side chat drawer; closing it (button or `Escape`) hides it.
- [ ] The drawer shows an empty-state message when there are no messages.
- [ ] Typing text and pressing Send (or `Enter`) adds the user message and a placeholder assistant
      reply to the history, and clears the input.
- [ ] The history scrolls and auto-scrolls to the newest message.
- [ ] Empty/whitespace input cannot be sent; Send is disabled when input is empty.
- [ ] No network requests are made anywhere in the app.
- [ ] Every future integration point is marked with a `// TODO:` comment.
- [ ] Keyboard focus is visible and the drawer/input are fully operable without a mouse.

---

## 11. Constraints summary (read before starting)

- Placeholders over polish. Structure is the deliverable.
- No backend, no LLM, no real data, no network calls — local state only.
- Keep the seams obvious and the components small so the real data layer drops in cleanly later.
- If a decision is ambiguous, pick the simpler option and leave a `// TODO:` noting the assumption.
