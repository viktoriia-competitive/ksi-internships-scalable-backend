import Link from "next/link";
import { AttemptPhaseBadge } from "@/components/AttemptPhaseBadge";
import { formatDateTime } from "@/lib/format";
import type { Attempt } from "@/lib/contracts";

export function AttemptHistory({ attempts, refreshing }: { attempts: Attempt[]; refreshing: boolean }) {
  if (attempts.length === 0) {
    return <div className="empty-state text-slate-500"><div className="text-sm font-bold text-slate-300">No attempts yet</div><div className="mt-1 text-xs">Your submitted solutions will appear here.</div></div>;
  }
  return (
    <div>
      {refreshing ? <div className="border-b border-white/10 px-4 py-2 font-mono text-[10px] text-slate-500">syncing judge state…</div> : null}
      <div className="divide-y divide-white/10">
        {attempts.map((attempt, index) => (
          <Link key={attempt.key} prefetch={false} href={`/attempts/${attempt.key}`} className="grid gap-3 px-4 py-4 transition hover:bg-white/[0.04] sm:grid-cols-[32px_minmax(0,1fr)_auto] sm:items-center sm:px-5">
            <span className="font-mono text-[10px] font-bold text-slate-600">#{attempts.length - index}</span>
            <div className="min-w-0">
              <div className="text-xs font-bold text-slate-200">{attempt.runtime}</div>
              <div className="mt-1 truncate font-mono text-[10px] text-slate-500">{formatDateTime(attempt.createdAt)}</div>
            </div>
            <AttemptPhaseBadge phase={attempt.phase} />
          </Link>
        ))}
      </div>
    </div>
  );
}
