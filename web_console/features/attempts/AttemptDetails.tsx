"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AttemptPhaseBadge } from "@/components/AttemptPhaseBadge";
import { readAttempt, readAttemptTimeline, attemptSourceUrl } from "@/lib/api/attempts";
import type { Attempt, LifecycleEvent } from "@/lib/contracts";

const TERMINAL = new Set(["passed", "wrong_output", "time_exceeded", "memory_exceeded", "runtime_failed", "build_failed", "platform_failed", "artifact_rejected"]);
function eventLabel(type: string) {
  return type
    .replace(/^execution\./, "")
    .replace(/^attempt\./, "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function ExecutionTimeline({ events }: { events: LifecycleEvent[] }) {
  if (!events.length) return null;
  return (
    <section className="surface overflow-hidden">
      <div className="border-b border-black/5 px-5 py-4">
        <p className="eyebrow">Execution log</p>
        <h2 className="mt-1 text-lg font-black text-ink-950">Derived from immutable facts.</h2>
      </div>
      <ol className="divide-y divide-black/5">
        {events.map((event) => (
          <li key={`${event.index}-${event.event}`} className="grid gap-2 px-5 py-4 sm:grid-cols-[3rem_1fr_auto] sm:items-center">
            <span className="font-mono text-xs font-bold text-slate-400">#{event.index}</span>
            <div>
              <div className="text-sm font-bold text-ink-950">{eventLabel(event.event)}</div>
              <div className="mt-1 font-mono text-[10px] text-slate-400">run {event.runKey.slice(0, 8)} · delivery {event.deliveryKey.slice(0, 8)}</div>
            </div>
            <time className="text-xs text-slate-400">{new Date(event.recordedAt).toLocaleTimeString()}</time>
          </li>
        ))}
      </ol>
    </section>
  );
}


function Preview({ label, text }: { label: string; text?: string | null }) {
  if (!text) return null;
  return (
    <section className="overflow-hidden rounded-2xl border border-black/10 bg-white">
      <div className="border-b border-black/5 px-4 py-3 text-[10px] font-black uppercase tracking-[0.14em] text-slate-400">{label}</div>
      <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words bg-ink-950 p-4 font-mono text-xs leading-6 text-slate-200">{text}</pre>
    </section>
  );
}

export function AttemptDetails({ attemptKey }: { attemptKey: string }) {
  const [attempt, setAttempt] = useState<Attempt>();
  const [events, setEvents] = useState<LifecycleEvent[]>([]);
  const [error, setError] = useState<string>();

  const load = useCallback(async () => {
    try {
      const [nextAttempt, nextEvents] = await Promise.all([
        readAttempt(attemptKey),
        readAttemptTimeline(attemptKey),
      ]);
      setAttempt(nextAttempt);
      setEvents(nextEvents);
      setError(undefined);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, [attemptKey]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!attempt || TERMINAL.has(attempt.phase)) return;
    const timer = window.setInterval(() => void load(), 2000);
    return () => window.clearInterval(timer);
  }, [attempt?.phase, load]);

  if (error) return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-800">{error}</div>;
  if (!attempt) return <div className="surface p-8 text-sm text-slate-500">Loading attempt…</div>;

  const result = attempt.report;
  const failure = result?.failure;

  return (
    <div className="space-y-6">
      <header>
        <Link href="/attempts" className="text-xs font-bold text-slate-400 hover:text-brand-600">← Attempt queue</Link>
        <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="eyebrow">Execution result</p>
            <h1 className="page-title mt-2">Attempt detail.</h1>
            <p className="mt-2 font-mono text-[11px] text-slate-400">{attempt.key}</p>
          </div>
          <AttemptPhaseBadge phase={attempt.phase} />
        </div>
      </header>

      <section className="dark-surface overflow-hidden">
        <div className="grid gap-px bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
          <div className="bg-ink-950 p-5"><div className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-500">Challenge</div><Link prefetch={false} href={`/challenges/${attempt.challenge.key}`} className="mt-2 block text-sm font-bold text-white hover:text-brand-500">{attempt.challenge.shortCode} · {attempt.challenge.name}</Link></div>
          <div className="bg-ink-950 p-5"><div className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-500">Language</div><div className="mt-2 text-sm font-bold text-white">{attempt.runtime}</div></div>
          <div className="bg-ink-950 p-5"><div className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-500">Cases</div><div className="mt-2 font-mono text-sm font-bold text-white">{result ? `${result.passedCases}/${result.totalCases}` : "—"}</div></div>
          <div className="bg-ink-950 p-5"><div className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-500">Peak</div><div className="mt-2 font-mono text-sm font-bold text-white">{result ? `${result.peakCpuMillis} ms · ${result.peakMemoryKiB} KiB` : "—"}</div></div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 px-5 py-4 text-xs text-slate-400">
          <span>{attempt.actor ? `@${attempt.actor}` : "anonymous"} · {attempt.artifact.fileName} · {attempt.artifact.bytes.toLocaleString()} bytes</span>
          <a className="font-bold text-brand-500 hover:text-brand-100" href={attemptSourceUrl(attempt.key)}>Download source ↓</a>
        </div>
      </section>

      <ExecutionTimeline events={events} />

      {result?.failureSummary ? <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5"><div className="eyebrow !text-amber-700">Evaluation summary</div><p className="mt-2 text-sm font-semibold leading-6 text-amber-950">{result.failureSummary}</p></div> : null}
      {result?.compilerLog ? <Preview label="Compiler output" text={result.compilerLog} /> : null}
      {failure ? <div className="grid gap-4 lg:grid-cols-2"><Preview label="Input" text={failure.stdinExcerpt} /><Preview label="Expected" text={failure.expectedExcerpt} /><Preview label="Actual" text={failure.actualExcerpt} /><Preview label="Stderr" text={failure.stderrExcerpt} /></div> : null}
      {attempt.sourceText ? <Preview label={attempt.sourceTruncated ? "Source · truncated" : "Source"} text={attempt.sourceText} /> : null}
    </div>
  );
}
