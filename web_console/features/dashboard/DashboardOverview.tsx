import Link from "next/link";
import { ChallengeLevelBadge } from "@/components/ChallengeLevelBadge";
import { AttemptPhaseBadge } from "@/components/AttemptPhaseBadge";
import { formatDateTime } from "@/lib/format";
import type { Challenge, Attempt } from "@/lib/contracts";

const TERMINAL = new Set(["passed", "wrong_output", "time_exceeded", "memory_exceeded", "runtime_failed", "build_failed", "platform_failed", "artifact_rejected"]);

function ArrowIcon() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M4 10h12M11 5l5 5-5 5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function DashboardOverview({ challenges, attempts }: { challenges: Challenge[]; attempts: Attempt[] }) {
  const accepted = attempts.filter((item) => item.phase === "passed").length;
  const active = attempts.filter((item) => !TERMINAL.has(item.phase)).length;
  const acceptance = attempts.length ? Math.round((accepted / attempts.length) * 100) : 0;

  return (
    <div className="space-y-6 sm:space-y-8">
      <section className="dark-surface relative overflow-hidden px-5 py-8 sm:px-8 sm:py-10 lg:px-10 lg:py-12">
        <div className="pointer-events-none absolute -right-16 -top-20 h-72 w-72 rounded-full border border-white/10" />
        <div className="pointer-events-none absolute -right-2 top-10 h-44 w-44 rounded-full border border-brand-500/40" />
        <div className="relative grid gap-8 lg:grid-cols-[1fr_auto] lg:items-end">
          <div className="max-w-3xl">
            <p className="eyebrow !text-brand-500">Competitive programming workspace</p>
            <h1 className="mt-3 text-4xl font-black tracking-[-0.055em] text-white sm:text-5xl lg:text-6xl">
              Code. Submit. <span className="text-brand-500">Know.</span>
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-6 text-slate-400 sm:text-base">
              A focused judge interface for moving from a challenge statement to a trusted verdict without dashboard noise.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/challenges" className="btn-accent gap-2">
                Browse challenges <ArrowIcon />
              </Link>
              <Link href="/attempts" className="inline-flex h-10 items-center justify-center rounded-xl border border-white/15 px-5 text-sm font-bold text-white transition hover:bg-white/10">
                Open judge queue
              </Link>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 lg:w-[420px]">
            <div className="bg-ink-900 p-4 sm:p-5">
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">Recent AC</div>
              <div className="mt-2 text-3xl font-black tracking-tight">{accepted}</div>
            </div>
            <div className="bg-ink-900 p-4 sm:p-5">
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">In flight</div>
              <div className="mt-2 text-3xl font-black tracking-tight">{active}</div>
            </div>
            <div className="bg-ink-900 p-4 sm:p-5">
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">AC rate</div>
              <div className="mt-2 text-3xl font-black tracking-tight">{acceptance}%</div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,0.75fr)]">
        <section className="surface overflow-hidden">
          <div className="card-header">
            <div>
              <p className="eyebrow">Live feed</p>
              <h2 className="mt-1 text-xl font-black tracking-tight">Recent judge activity</h2>
            </div>
            <Link href="/attempts" className="card-action">View queue</Link>
          </div>
          <div className="divide-y divide-black/5">
            {attempts.length === 0 ? (
              <div className="empty-state text-sm text-slate-500">No attempts yet.</div>
            ) : attempts.map((attempt) => (
              <Link
                key={attempt.key}
                prefetch={false}
                href={`/attempts/${attempt.key}`}
                className="grid gap-3 px-5 py-4 transition hover:bg-brand-50/40 sm:grid-cols-[105px_minmax(0,1fr)_auto] sm:items-center sm:px-6"
              >
                <span className="font-mono text-[10px] text-slate-400">{formatDateTime(attempt.createdAt)}</span>
                <div className="min-w-0">
                  <div className="flex min-w-0 items-baseline gap-2">
                    <span className="task-code shrink-0">{attempt.challenge.shortCode}</span>
                    <span className="truncate text-sm font-bold text-ink-950">{attempt.challenge.name}</span>
                  </div>
                  <div className="mt-1 text-[11px] text-slate-400">{attempt.runtime}{attempt.actor ? ` · @${attempt.actor}` : ""}</div>
                </div>
                <AttemptPhaseBadge phase={attempt.phase} />
              </Link>
            ))}
          </div>
        </section>

        <section className="surface overflow-hidden">
          <div className="card-header">
            <div>
              <p className="eyebrow">Popular now</p>
              <h2 className="mt-1 text-xl font-black tracking-tight">Challenges to try</h2>
            </div>
            <Link href="/challenges" className="card-action">Catalog</Link>
          </div>
          <div className="divide-y divide-black/5">
            {challenges.map((challenge, index) => (
              <Link key={challenge.key} prefetch={false} href={`/challenges/${challenge.key}`} className="group flex gap-4 px-5 py-4 transition hover:bg-brand-50/40 sm:px-6">
                <span className="font-mono text-xs font-bold text-slate-300">{String(index + 1).padStart(2, "0")}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="task-code">{challenge.shortCode}</div>
                      <div className="mt-0.5 truncate text-sm font-bold text-ink-950 group-hover:text-brand-600">{challenge.name}</div>
                    </div>
                    <ChallengeLevelBadge level={challenge.level} />
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-3">
                    <div className="flex min-w-0 gap-1 overflow-hidden">
                      {challenge.labels.slice(0, 2).map((tag) => <span key={tag} className="tag shrink-0">{tag}</span>)}
                    </div>
                    <span className="muted-meta shrink-0">{challenge.acceptedCount.toLocaleString()} solves</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
