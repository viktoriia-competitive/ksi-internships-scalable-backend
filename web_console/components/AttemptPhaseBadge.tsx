import { Badge } from "@/components/ui/Badge";
import type { AttemptPhase } from "@/lib/contracts";

type PhasePresentation = Readonly<{ label: string; tone: string }>;

const PHASE_PRESENTATION: Record<AttemptPhase, PhasePresentation> = {
  waiting: { label: "Waiting", tone: "badge-queued" },
  executing: { label: "Executing", tone: "badge-running" },
  passed: { label: "Passed", tone: "badge-accepted" },
  wrong_output: { label: "Wrong output", tone: "badge-wrong" },
  time_exceeded: { label: "Time exceeded", tone: "badge-tle" },
  memory_exceeded: { label: "Memory exceeded", tone: "badge-tle" },
  runtime_failed: { label: "Runtime failed", tone: "badge-re" },
  platform_failed: { label: "Platform failed", tone: "badge-re" },
  build_failed: { label: "Build failed", tone: "badge-ce" },
  artifact_rejected: { label: "Artifact rejected", tone: "badge-ce" },
};

export function AttemptPhaseBadge({ phase }: { phase: AttemptPhase }) {
  const view = PHASE_PRESENTATION[phase];
  return <Badge tone={view.tone}>{view.label}</Badge>;
}
