export type Role = "user" | "assistant";

export interface Message {
  id: string; // any unique id, e.g. crypto.randomUUID()
  role: Role;
  content: string;
  createdAt: number; // Date.now()
}

export interface Company {
  id: string;
  name: string;
}
