import type {
  Attempt,
  AttemptCollection,
  AttemptPhase,
  LifecycleTimeline,
  OpenAttemptRequest,
  OpenAttemptResponse,
  RuntimeName,
} from "@/lib/contracts";
import { requestJson } from "@/lib/http/request";
import { apiResource } from "./resource";

export type AttemptFilter = {
  page?: number;
  size?: number;
  challenge?: string;
  phase?: AttemptPhase | string;
  actor?: string;
};

const attempts = apiResource("attempts");

function pageFilter(filter: AttemptFilter) {
  return {
    page: filter.page ?? 1,
    size: filter.size ?? 40,
    challenge: filter.challenge,
    phase: filter.phase,
    actor: filter.actor,
  };
}

export function browseAttempts(filter: AttemptFilter = {}): Promise<AttemptCollection> {
  return attempts.list<AttemptCollection>({ query: pageFilter(filter), cache: "no-store" });
}

export function browseChallengeAttempts(
  challengeKey: string,
  filter: Pick<AttemptFilter, "page" | "size" | "phase"> = {},
): Promise<AttemptCollection> {
  return requestJson<AttemptCollection>(`/challenges/${encodeURIComponent(challengeKey)}/attempts`, {
    query: pageFilter(filter),
    cache: "no-store",
  });
}

export function readAttempt(key: string): Promise<Attempt> {
  return attempts.read<Attempt>(key, "", { cache: "no-store" });
}

export async function readAttemptTimeline(key: string) {
  const timeline = await attempts.read<LifecycleTimeline>(key, "/timeline", { cache: "no-store" });
  return timeline.entries;
}

export function attemptSourceUrl(key: string): string {
  return attempts.url(key, "/source");
}

export function openAttempt(input: {
  challengeKey: string;
  runtime: RuntimeName | string;
  sourceText: string;
  artifactName?: string;
  mediaType?: string;
}): Promise<OpenAttemptResponse> {
  const payload: OpenAttemptRequest = {
    challengeKey: input.challengeKey,
    runtime: input.runtime as RuntimeName,
    sourceText: input.sourceText,
    artifactName: input.artifactName,
    mediaType: input.mediaType,
  };
  return attempts.create<OpenAttemptResponse>(payload);
}
