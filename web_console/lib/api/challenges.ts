import type { ChallengeCollection, ChallengeFilter, ChallengeView } from "@/lib/contracts";
import { apiResource } from "./resource";

const catalogue = apiResource("challenges");
const DEFAULT_FILTER = Object.freeze({
  level: "all",
  label: "all",
  mode: "all",
  orderBy: "shortCode",
  direction: "asc",
  page: 1,
  size: 40,
});

export function browseChallenges(
  filter: ChallengeFilter = {},
  options?: { cache?: RequestCache; next?: { revalidate?: number | false } },
): Promise<ChallengeCollection> {
  return catalogue.list<ChallengeCollection>({
    query: { ...DEFAULT_FILTER, ...filter },
    cache: options?.cache ?? "no-store",
    next: options?.next,
  });
}

export function readChallenge(key: string, options?: { cache?: RequestCache }): Promise<ChallengeView> {
  return catalogue.read<ChallengeView>(key, "", { cache: options?.cache ?? "no-store" });
}
