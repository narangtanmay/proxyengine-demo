import type { Company } from "./types";

// TODO: replace this hardcoded list with a real GET /companies call to the backend.
export const COMPANIES: Company[] = [
  { id: "acme", name: "Acme Corporation" },
  { id: "globex", name: "Globex Corporation" },
  { id: "initech", name: "Initech" },
  { id: "umbrella", name: "Umbrella Corporation" },
];

// Fixed placeholder returned in place of a real assistant response.
// TODO: remove once the chat is wired to a real POST /query call to the backend.
export const PLACEHOLDER_ASSISTANT_REPLY =
  "The assistant isn't connected yet — this is a placeholder reply.";
