import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, sendChat, streamChat } from "../services/api";
import type { ChatMessage, ChatRequest, ConversationMessage, Source } from "../types/chat";

const STORAGE_KEY = "national-parks-chat-history-v1";
const MAX_STORED_MESSAGES = 40;
const MAX_BACKEND_HISTORY = 20;

function createId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function loadStoredMessages(): ChatMessage[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];

    const parsed = JSON.parse(raw) as ChatMessage[];
    if (!Array.isArray(parsed)) return [];

    return parsed
      .filter(
        (message) =>
          message &&
          typeof message.id === "string" &&
          (message.role === "user" || message.role === "assistant") &&
          typeof message.content === "string",
      )
      .map((message) => ({
        ...message,
        state: message.state === "error" ? "error" : "complete",
      }))
      .slice(-MAX_STORED_MESSAGES);
  } catch {
    return [];
  }
}

function toBackendHistory(messages: ChatMessage[]): ConversationMessage[] {
  return messages
    .filter((message) => message.state !== "error" && message.content.trim().length > 0)
    .map(({ role, content }) => ({ role, content }))
    .slice(-MAX_BACKEND_HISTORY);
}

function friendlyError(error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") {
    return "Response stopped.";
  }
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) {
    return "Could not reach the backend. Confirm that FastAPI is running on port 8000 and VITE_API_URL is correct.";
  }
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred while generating the answer.";
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>(loadStoredMessages);
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_STORED_MESSAGES)));
  }, [messages]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const updateAssistant = useCallback(
    (id: string, update: (message: ChatMessage) => ChatMessage) => {
      setMessages((current) =>
        current.map((message) => (message.id === id ? update(message) : message)),
      );
    },
    [],
  );

  const sendMessage = useCallback(
    async (rawQuestion: string) => {
      const question = rawQuestion.trim();
      if (!question || isLoading) return;

      const history = toBackendHistory(messages);
      const userMessage: ChatMessage = {
        id: createId(),
        role: "user",
        content: question,
        state: "complete",
        createdAt: new Date().toISOString(),
      };
      const assistantId = createId();
      const assistantMessage: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        state: "streaming",
        createdAt: new Date().toISOString(),
        sources: [],
      };

      setMessages((current) => [...current, userMessage, assistantMessage]);
      setIsLoading(true);

      const controller = new AbortController();
      abortRef.current = controller;

      const request: ChatRequest = {
        question,
        top_k: 5,
        conversation_history: history.length ? history : undefined,
      };

      let receivedToken = false;

      try {
        await streamChat(
          request,
          {
            onToken: (token) => {
              receivedToken = true;
              updateAssistant(assistantId, (message) => ({
                ...message,
                content: message.content + token,
                state: "streaming",
              }));
            },
            onDone: (event) => {
              updateAssistant(assistantId, (message) => ({
                ...message,
                state: "complete",
                sources: event.sources || [],
              }));
            },
          },
          controller.signal,
        );

        updateAssistant(assistantId, (message) => ({
          ...message,
          state: message.content.trim() ? "complete" : message.state,
        }));
      } catch (streamError) {
        const wasAborted = controller.signal.aborted;

        if (!receivedToken && !wasAborted) {
          try {
            const response = await sendChat(request, controller.signal);
            updateAssistant(assistantId, (message) => ({
              ...message,
              content: response.answer,
              sources: response.sources || [],
              state: "complete",
            }));
            return;
          } catch (fallbackError) {
            updateAssistant(assistantId, (message) => ({
              ...message,
              content: friendlyError(fallbackError),
              state: "error",
            }));
            return;
          }
        }

        updateAssistant(assistantId, (message) => ({
          ...message,
          content: message.content || friendlyError(streamError),
          state: wasAborted ? "complete" : "error",
        }));
      } finally {
        abortRef.current = null;
        setIsLoading(false);
      }
    },
    [isLoading, messages, updateAssistant],
  );

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const clearMessages = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return {
    messages,
    isLoading,
    sendMessage,
    stopGeneration,
    clearMessages,
  };
}
