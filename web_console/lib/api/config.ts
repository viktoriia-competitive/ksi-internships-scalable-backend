import { readHttpConfig } from "@/lib/http/config";

export function getApiBaseUrl(): string {
  return readHttpConfig().baseUrl;
}

export const API_PREFIX = "/control/v2";
export const API_TIMEOUT_MS = 12_000;
