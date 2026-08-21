import { Badge } from "@/components/ui/Badge";
import type { ChallengeLevel } from "@/lib/contracts";

const levelTone: Record<ChallengeLevel, string> = {
  easy: "badge-easy",
  medium: "badge-medium",
  hard: "badge-hard",
};

export function ChallengeLevelBadge({ level }: { level: ChallengeLevel }) {
  return (
    <Badge tone={levelTone[level]} className="capitalize">
      {level}
    </Badge>
  );
}
