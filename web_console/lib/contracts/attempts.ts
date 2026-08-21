export type AttemptPhase =
  | "waiting"
  | "executing"
  | "passed"
  | "wrong_output"
  | "time_exceeded"
  | "memory_exceeded"
  | "runtime_failed"
  | "build_failed"
  | "platform_failed"
  | "artifact_rejected";

export type RuntimeName = "C++" | "Python" | "Java" | "Rust" | "Go" | "SQL" | "Bash";

export interface ArtifactView {
  digest: string;
  fileName: string;
  mediaType: string;
  bytes: number;
}

export interface ChallengeRef {
  key: string;
  shortCode: string;
  name: string;
}

export interface CaseReport {
  case: string;
  outcome: string;
  cpuMillis: number;
  memoryKiB: number;
  note: string;
}

export interface FailureReport {
  case?: string | null;
  summary: string;
  stdinExcerpt: string;
  expectedExcerpt: string;
  actualExcerpt: string;
  stderrExcerpt: string;
}

export interface EvaluationReport {
  passedCases: number;
  totalCases: number;
  peakCpuMillis: number;
  peakMemoryKiB: number;
  compilerLog: string;
  failureSummary: string;
  failure?: FailureReport | null;
  cases?: CaseReport[];
}

export interface Attempt {
  key: string;
  createdAt: string;
  challenge: ChallengeRef;
  phase: AttemptPhase;
  runtime: string;
  artifact: ArtifactView;
  actor?: string | null;
  report?: EvaluationReport | null;
  sourceText?: string | null;
  sourceTruncated?: boolean;
}

export interface AttemptCollection {
  entries: Attempt[];
  pageInfo: { index: number; size: number; totalEntries: number; totalPages: number };
}

export interface LifecycleEvent {
  index: number;
  event: string;
  recordedAt: string;
  runKey: string;
  deliveryKey: string;
  attributes: Record<string, unknown>;
}

export interface LifecycleTimeline {
  entries: LifecycleEvent[];
}

export interface OpenAttemptRequest {
  challengeKey: string;
  runtime: RuntimeName;
  sourceText: string;
  artifactName?: string;
  mediaType?: string;
}

export interface OpenAttemptResponse {
  attempt: Attempt;
  links: { self: string; events: string; source: string };
}

export const RUNTIMES: readonly RuntimeName[] = ["C++", "Python", "Java", "Rust", "Go", "SQL", "Bash"] as const;

export function isRuntimeName(value: string): value is RuntimeName {
  return (RUNTIMES as readonly string[]).includes(value);
}
