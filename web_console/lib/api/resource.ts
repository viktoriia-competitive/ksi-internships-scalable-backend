import { absoluteApiUrl, requestJson, type RequestOptions } from "@/lib/http/request";

export function apiResource(root: string) {
  const base = root.startsWith("/") ? root : `/${root}`;
  return {
    list<T>(options: RequestOptions = {}): Promise<T> {
      return requestJson<T>(base, options);
    },
    read<T>(id: string, suffix = "", options: RequestOptions = {}): Promise<T> {
      const encoded = encodeURIComponent(id);
      return requestJson<T>(`${base}/${encoded}${suffix}`, options);
    },
    create<T>(body: unknown, options: RequestOptions = {}): Promise<T> {
      return requestJson<T>(base, { ...options, method: "POST", body });
    },
    url(id: string, suffix = ""): string {
      return absoluteApiUrl(`${base}/${encodeURIComponent(id)}${suffix}`);
    },
  } as const;
}
