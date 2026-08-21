"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AttemptPhaseBadge } from "@/components/AttemptPhaseBadge";
import { browseAttempts } from "@/lib/api/attempts";
import { formatDateTime } from "@/lib/format";
import type { Attempt } from "@/lib/contracts";

const TERMINAL = new Set(["passed", "wrong_output", "time_exceeded", "memory_exceeded", "runtime_failed", "build_failed", "platform_failed", "artifact_rejected"]);

export function AttemptQueue() {
  const [items, setItems] = useState<Attempt[]>([]);
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);
  const pending = useMemo(() => items.some((item) => !TERMINAL.has(item.phase)), [items]);
  const accepted = useMemo(() => items.filter((item) => item.phase === "passed").length, [items]);

  const refresh = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const result = await browseAttempts({ page: 1, size: 40 });
      setItems(result.entries);
      setError(undefined);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      if (showLoading) setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(true); }, [refresh]);
  useEffect(() => {
    if (!pending) return;
    const timer = window.setInterval(() => void refresh(false), 3000);
    return () => window.clearInterval(timer);
  }, [pending, refresh]);

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="eyebrow">Judge activity</p>
          <h1 className="page-title mt-2">Attempt queue.</h1>
          <p className="page-copy mt-2">Track recent executions as they move through the queue and into isolated judge workers.</p>
        </div>
        <div className="grid grid-cols-3 gap-2 sm:w-auto">
          <div className="rounded-xl border border-black/10 bg-white px-4 py-3"><div className="font-mono text-lg font-black">{items.length}</div><div className="text-[9px] font-bold uppercase tracking-[0.1em] text-slate-400">recent</div></div>
          <div className="rounded-xl border border-black/10 bg-white px-4 py-3"><div className="font-mono text-lg font-black text-emerald-600">{accepted}</div><div className="text-[9px] font-bold uppercase tracking-[0.1em] text-slate-400">accepted</div></div>
          <div className="rounded-xl border border-black/10 bg-white px-4 py-3"><div className="font-mono text-lg font-black text-amber-600">{items.filter((item) => !TERMINAL.has(item.phase)).length}</div><div className="text-[9px] font-bold uppercase tracking-[0.1em] text-slate-400">active</div></div>
        </div>
      </header>

      {error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">API error: {error}</div> : null}

      <section className="surface overflow-hidden">
        <div className="flex items-center justify-between border-b border-black/5 px-5 py-4 sm:px-6">
          <div>
            <div className="text-sm font-black text-ink-950">Execution stream</div>
            <div className="mt-0.5 text-xs text-slate-400">{pending ? "Live refresh every 3 seconds" : "All visible jobs are settled"}</div>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400"><span className={`h-2 w-2 rounded-full ${pending ? "bg-amber-400" : "bg-emerald-400"}`} />{pending ? "processing" : "idle"}</div>
        </div>

        {loading ? (
          <div className="empty-state"><p className="text-sm font-semibold text-slate-500">Loading queue…</p></div>
        ) : items.length === 0 ? (
          <div className="empty-state"><p className="text-sm font-semibold text-slate-700">No attempts yet</p><Link href="/challenges" className="mt-3 text-xs font-bold text-brand-600">Pick a challenge →</Link></div>
        ) : (
          <div className="divide-y divide-black/5">
            {items.map((attempt) => (
              <Link key={attempt.key} prefetch={false} href={`/attempts/${attempt.key}`} className="group grid gap-3 px-5 py-4 transition hover:bg-brand-50/40 sm:px-6 lg:grid-cols-[145px_minmax(0,1fr)_120px_150px] lg:items-center">
                <div className="font-mono text-[10px] text-slate-400">{formatDateTime(attempt.createdAt)}</div>
                <div className="min-w-0">
                  <div className="flex min-w-0 items-center gap-2"><span className="task-code shrink-0">{attempt.challenge.shortCode}</span><span className="truncate text-sm font-bold text-ink-950 group-hover:text-brand-600">{attempt.challenge.name}</span></div>
                  <div className="mt-1 font-mono text-[10px] text-slate-400">{attempt.key.slice(0, 12)}…</div>
                </div>
                <div className="text-xs font-semibold text-slate-600">{attempt.runtime}</div>
                <div className="flex items-center justify-between gap-3 lg:justify-end"><span className="text-xs text-slate-400 lg:hidden">{attempt.actor ? `@${attempt.actor}` : "anonymous"}</span><AttemptPhaseBadge phase={attempt.phase} /></div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
