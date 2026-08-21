import { readHttpConfig } from "./config";
import { JsonTransport, TransportError, type JsonRequest, type ScalarQuery } from "./transport";

const transport = new JsonTransport();

export { TransportError as HttpError };
export type QueryValue = ScalarQuery;
export type RequestOptions = JsonRequest;

export function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return transport.json<T>(path, options);
}

export function absoluteApiUrl(path: string): string {
  return transport.url(path);
}

export async function checkHealth(): Promise<{ state: string }> {
  const config = readHttpConfig();
  const controller = new AbortController();
  const deadline = globalThis.setTimeout(() => controller.abort(), config.timeoutMs);
  try {
    const response = await fetch(new URL("/live", `${config.baseUrl}/`), {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) throw new TransportError("health check failed", response.status);
    return response.json() as Promise<{ state: string }>;
  } finally {
    globalThis.clearTimeout(deadline);
  }
}
