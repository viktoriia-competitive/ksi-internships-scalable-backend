import Link from "next/link";
import { ChallengeLevelBadge } from "@/components/ChallengeLevelBadge";
import type { Challenge } from "@/lib/contracts";

export function ChallengeTable({ items }: { items: Challenge[] }) {
  if (items.length === 0) {
    return <div className="empty-state"><p className="text-sm font-semibold text-slate-700">No matching challenges</p><p className="mt-1 text-xs text-slate-400">Try removing one of the filters.</p></div>;
  }

  return (
    <div className="divide-y divide-black/5">
      {items.map((challenge) => (
        <Link key={challenge.key} href={`/challenges/${challenge.key}`} prefetch={false} className="group grid gap-3 px-5 py-4 transition hover:bg-brand-50/50 sm:px-6 lg:grid-cols-[minmax(0,1fr)_220px_120px] lg:items-center">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="task-code">{challenge.shortCode}</span>
              {challenge.score != null ? <span className="font-mono text-[10px] text-slate-400">#{challenge.score}</span> : null}
            </div>
            <div className="mt-1 truncate text-[15px] font-bold tracking-tight text-ink-950 group-hover:text-brand-600">{challenge.name}</div>
            <div className="mt-2 flex flex-wrap gap-1">
              {challenge.labels.slice(0, 4).map((tag) => <span key={tag} className="tag">{tag}</span>)}
              {challenge.labels.length > 4 ? <span className="tag">+{challenge.labels.length - 4}</span> : null}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 lg:justify-start">
            <ChallengeLevelBadge level={challenge.level} />
            <span className="tag capitalize">{challenge.mode}</span>
            {challenge.interactive ? <span className="tag">interactive</span> : null}
          </div>
          <div className="flex items-center justify-between gap-4 lg:block lg:text-right">
            <span className="text-xs text-slate-400 lg:hidden">Solved</span>
            <div className="font-mono text-sm font-bold tabular-nums text-slate-700">{challenge.acceptedCount.toLocaleString()}</div>
            <div className="mt-0.5 hidden text-[10px] uppercase tracking-[0.1em] text-slate-400 lg:block">solves</div>
          </div>
        </Link>
      ))}
    </div>
  );
}
