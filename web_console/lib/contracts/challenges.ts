export type ChallengeLevel = "easy" | "medium" | "hard";
export type ChallengeMode = "stdio" | "interactive" | "library" | "sql" | "bash" | "archive";

export interface ResourceBudget {
  cpuMillis: number;
  memoryMiB: number;
}

export interface OriginRef {
  provider?: string | null;
  link?: string | null;
}

export interface Challenge {
  key: string;
  shortCode: string;
  name: string;
  level: ChallengeLevel;
  score?: number | null;
  acceptedCount: number;
  labels: string[];
  mode: ChallengeMode;
  runtimes: string[];
  budget: ResourceBudget;
  customChecker: boolean;
  interactive: boolean;
  origin?: OriginRef | null;
}

export interface ExampleCase {
  stdin: string;
  stdout: string;
  explanation?: string | null;
}

export interface ChallengePrompt {
  overview: string;
  inputContract?: string | null;
  outputContract?: string | null;
  interactionContract?: string | null;
  notes?: string | null;
  markdown?: string | null;
}

export interface EvaluationPolicy {
  inputMode: string;
  inputFile?: string | null;
  outputFile?: string | null;
  checker: string;
  checkerOptions?: Record<string, unknown> | null;
  testCount?: number | null;
  visibleTests?: number | null;
}

export interface SourcePolicy {
  artifactType: string;
  extensions: string[];
  entrypoint?: string | null;
}

export interface ChallengeView extends Challenge {
  derivedBudget: boolean;
  prompt: ChallengePrompt;
  examples: ExampleCase[];
  evaluation: EvaluationPolicy;
  sourcePolicy: SourcePolicy;
  referenceSolutions: number;
}

export interface PageInfo {
  index: number;
  size: number;
  totalEntries: number;
  totalPages: number;
}

export interface ChallengeCollection {
  entries: Challenge[];
  pageInfo: PageInfo;
}

export type ChallengeOrder = "shortCode" | "name" | "level" | "acceptedCount" | "key" | "score" | "mode";

export interface ChallengeFilter {
  search?: string;
  level?: ChallengeLevel | "all";
  label?: string | "all";
  mode?: ChallengeMode | "all";
  orderBy?: ChallengeOrder;
  direction?: "asc" | "desc";
  page?: number;
  size?: number;
}

const DEFAULT_BUDGET: ResourceBudget = { cpuMillis: 2000, memoryMiB: 256 };

export function challengeBudget(challenge: Pick<Challenge, "budget">): ResourceBudget {
  return challenge.budget ?? DEFAULT_BUDGET;
}
