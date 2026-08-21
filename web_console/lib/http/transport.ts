import { readHttpConfig } from "./config";

export type ScalarQuery = string | number | boolean | null | undefined;

export type JsonRequest = Readonly<{
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, ScalarQuery>;
  headers?: HeadersInit;
  cache?: RequestCache;
  next?: { revalidate?: number | false };
  timeoutMs?: number;
}>;

export class TransportError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly responseBody?: unknown,
  ) {
    super(message);
    this.name = "TransportError";
  }
}

export class JsonTransport {
  private readonly baseUrl: string;
  private readonly apiPrefix: string;
  private readonly defaultTimeoutMs: number;

  constructor() {
    const config = readHttpConfig();
    this.baseUrl = config.baseUrl;
    this.apiPrefix = config.apiPrefix;
    this.defaultTimeoutMs = config.timeoutMs;
  }

  url(path: string, query?: Record<string, ScalarQuery>): string {
    const pathname = path.startsWith("/") ? path : `/${path}`;
    const versionedPath = pathname.startsWith(this.apiPrefix)
      ? pathname
      : `${this.apiPrefix}${pathname}`;
    const target = new URL(versionedPath, `${this.baseUrl}/`);

    for (const [name, value] of Object.entries(query ?? {})) {
      if (value === undefined || value === null || value === "") continue;
      target.searchParams.append(name, String(value));
    }
    return target.toString();
  }

  async json<T>(path: string, request: JsonRequest = {}): Promise<T> {
    const timeoutMs = request.timeoutMs ?? this.defaultTimeoutMs;
    const controller = new AbortController();
    const deadline = globalThis.setTimeout(() => controller.abort(), timeoutMs);
    const serialized = request.body === undefined ? undefined : JSON.stringify(request.body);
    const headers = new Headers(request.headers);
    headers.set("Accept", "application/json");
    if (serialized !== undefined && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    try {
      const response = await fetch(this.url(path, request.query), {
        method: request.method ?? (serialized === undefined ? "GET" : "POST"),
        body: serialized,
        headers,
        signal: controller.signal,
        cache: request.cache,
        next: request.next,
      });
      const payload = await parsePayload(response);
      if (!response.ok) {
        throw new TransportError(describeFailure(response, payload), response.status, payload);
      }
      return payload as T;
    } catch (error) {
      if (error instanceof TransportError) throw error;
      if (error instanceof Error && error.name === "AbortError") {
        throw new TransportError(`API timeout after ${timeoutMs} ms`, 0);
      }
      throw new TransportError(error instanceof Error ? error.message : "API request failed", 0);
    } finally {
      globalThis.clearTimeout(deadline);
    }
  }
}

async function parsePayload(response: Response): Promise<unknown> {
  const raw = await response.text();
  if (!raw) return null;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("json")) {
    try {
      return JSON.parse(raw);
    } catch {
      return raw;
    }
  }
  return raw;
}

function describeFailure(response: Response, payload: unknown): string {
  if (payload && typeof payload === "object" && "error" in payload) {
    const envelope = (payload as { error?: { message?: unknown } }).error;
    return String(envelope?.message ?? response.statusText);
  }
  if (typeof payload === "string" && payload.trim()) return payload.trim();
  return response.statusText || `HTTP ${response.status}`;
}
