export type ChatRole = "user" | "assistant";
export type MessageState = "complete" | "streaming" | "error";

export interface ConversationMessage {
  role: ChatRole;
  content: string;
}

export interface Source {
  park_name: string;
  park_code: string;
  url: string;
  score: number;
}

export interface ChatMessage extends ConversationMessage {
  id: string;
  createdAt: string;
  state: MessageState;
  sources?: Source[];
}

export interface ChatRequest {
  question: string;
  top_k?: number;
  park_code?: string;
  conversation_history?: ConversationMessage[];
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  question: string;
  num_sources: number;
  active_park_code?: string | null;
}

export interface HealthResponse {
  status: string;
  message: string;
  version: string;
}

export interface StreamDoneEvent {
  type: "done";
  sources?: Source[];
  num_sources?: number;
  active_park_code?: string | null;
}

export type BackendStatus = "checking" | "online" | "offline";
