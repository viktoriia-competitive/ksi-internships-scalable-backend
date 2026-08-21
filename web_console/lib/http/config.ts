export type HttpRuntimeConfig = Readonly<{
  baseUrl: string;
  apiPrefix: string;
  timeoutMs: number;
}>;

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

/**
 * The UI has two networking contexts in development:
 *
 * - React Server Components run in the Next.js Docker container, where the API
 *   is reachable through Docker DNS as http://api:8000.
 * - Client Components run in the user's browser, where Docker service names do
 *   not resolve and the published API is http://localhost:8000.
 *
 * Keeping separate server/public URLs avoids the classic "127.0.0.1 points to
 * the wrong container" failure while preserving host-based local development.
 */
export function readHttpConfig(): HttpRuntimeConfig {
  const isServer = typeof window === "undefined";
  const serverBaseUrl =
    process.env.API_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_URL?.trim() ||
    "http://127.0.0.1:8000";
  const browserBaseUrl =
    process.env.NEXT_PUBLIC_API_URL?.trim() || "http://127.0.0.1:8000";

  return {
    baseUrl: trimTrailingSlash(isServer ? serverBaseUrl : browserBaseUrl),
    apiPrefix: "/control/v2",
    timeoutMs: 12_000,
  };
}
