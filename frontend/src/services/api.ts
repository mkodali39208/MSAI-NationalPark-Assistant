import type {
  ChatRequest,
  ChatResponse,
  HealthResponse,
  StreamDoneEvent,
} from "../types/chat";

const configuredUrl = import.meta.env.VITE_API_URL?.trim();
export const API_BASE_URL = (configuredUrl || "http://127.0.0.1:8000").replace(/\/$/, "");

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string; message?: string };
    return payload.detail || payload.message || `Request failed with status ${response.status}`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

export async function checkHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: "GET",
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new ApiError(await getErrorMessage(response), response.status);
  }

  return (await response.json()) as HealthResponse;
}

export async function sendChat(request: ChatRequest, signal?: AbortSignal): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    throw new ApiError(await getErrorMessage(response), response.status);
  }

  return (await response.json()) as ChatResponse;
}

interface StreamHandlers {
  onToken: (token: string) => void;
  onDone: (event: StreamDoneEvent) => void;
}

function parseSseBlock(block: string): string[] {
  return block
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart());
}

export async function streamChat(
  request: ChatRequest,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    throw new ApiError(await getErrorMessage(response), response.status);
  }

  if (!response.body) {
    throw new ApiError("The browser could not read the streaming response.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const processBlock = (block: string): boolean => {
    const dataLines = parseSseBlock(block);

    for (const data of dataLines) {
      if (!data) continue;
      if (data === "[DONE]") return true;

      let event: unknown;
      try {
        event = JSON.parse(data);
      } catch {
        continue;
      }

      if (!event || typeof event !== "object" || !("type" in event)) continue;

      const typedEvent = event as {
        type: string;
        content?: string;
        message?: string;
        sources?: StreamDoneEvent["sources"];
        num_sources?: number;
        active_park_code?: string | null;
      };

      if (typedEvent.type === "token" && typeof typedEvent.content === "string") {
        handlers.onToken(typedEvent.content);
      } else if (typedEvent.type === "done") {
        handlers.onDone({
          type: "done",
          sources: typedEvent.sources,
          num_sources: typedEvent.num_sources,
          active_park_code: typedEvent.active_park_code,
        });
      } else if (typedEvent.type === "error") {
        throw new ApiError(typedEvent.message || "The backend returned a streaming error.");
      }
    }

    return false;
  };

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";

    for (const block of blocks) {
      if (processBlock(block)) return;
    }

    if (done) {
      if (buffer.trim()) processBlock(buffer);
      return;
    }
  }
}
