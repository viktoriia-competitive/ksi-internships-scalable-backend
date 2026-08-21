import Link from "next/link";
import { ChallengeLevelBadge } from "@/components/ChallengeLevelBadge";
import type { ChallengeView } from "@/lib/contracts";
import { challengeBudget } from "@/lib/contracts";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-400">{label}</dt>
      <dd className="mt-1 truncate font-mono text-xs font-bold text-slate-700">{value}</dd>
    </div>
  );
}

export function ChallengeStatement({ challenge: p }: { challenge: ChallengeView }) {
  const prompt = p.prompt;
  const budget = challengeBudget(p);
  const isSpecialJudge = p.customChecker || p.evaluation.checker === "custom";

  return (
    <article className="surface overflow-hidden">
      <div className="border-b border-black/5 px-5 py-6 sm:px-7 sm:py-7">
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/challenges" className="text-xs font-bold text-slate-400 transition hover:text-brand-600">Challenges</Link>
          <span className="text-slate-300">/</span>
          <span className="task-code">{p.shortCode}</span>
        </div>

        <div className="mt-4 flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="eyebrow">Challenge</p>
            <h1 className="mt-2 text-3xl font-black tracking-[-0.04em] text-ink-950 sm:text-4xl">{p.name}</h1>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <ChallengeLevelBadge level={p.level} />
              <span className="tag capitalize">{p.mode}</span>
              {isSpecialJudge ? <span className="tag">special judge</span> : null}
              {p.interactive ? <span className="tag">interactive</span> : null}
              {p.score != null ? <span className="tag">rating {p.score}</span> : null}
            </div>
          </div>

          <div className="grid shrink-0 grid-cols-2 gap-x-8 gap-y-4 rounded-2xl border border-black/5 bg-slate-50 px-5 py-4 sm:min-w-[250px]">
            <Stat label="CPU" value={`${budget.cpuMillis} ms${p.derivedBudget ? "*" : ""}`} />
            <Stat label="Memory" value={`${budget.memoryMiB} MiB`} />
            <Stat label="I/O" value={p.evaluation.inputMode} />
            <Stat label="Solved" value={p.acceptedCount.toLocaleString()} />
          </div>
        </div>

        {p.labels.length ? (
          <div className="mt-5 flex flex-wrap gap-1.5 border-t border-black/5 pt-4">
            {p.labels.map((tag) => <span key={tag} className="tag">{tag}</span>)}
          </div>
        ) : null}
      </div>

      <div className="space-y-8 px-5 py-7 sm:px-7 sm:py-8">
        <section>
          <h2 className="statement-h">Challenge statement</h2>
          <p className="statement-p whitespace-pre-wrap">{prompt.overview}</p>
        </section>

        {prompt.inputContract ? <section><h2 className="statement-h">Input</h2><p className="statement-p whitespace-pre-wrap">{prompt.inputContract}</p></section> : null}
        {prompt.outputContract ? <section><h2 className="statement-h">Output</h2><p className="statement-p whitespace-pre-wrap">{prompt.outputContract}</p></section> : null}
        {prompt.interactionContract ? <section><h2 className="statement-h">Interaction</h2><p className="statement-p whitespace-pre-wrap">{prompt.interactionContract}</p></section> : null}
        {prompt.notes ? <section><h2 className="statement-h">Notes</h2><p className="statement-p whitespace-pre-wrap">{prompt.notes}</p></section> : null}

        <section>
          <div className="mb-4 flex items-center justify-between gap-4">
            <h2 className="statement-h !mb-0">Examples</h2>
            {p.examples.length ? <span className="font-mono text-[10px] text-slate-400">{p.examples.length} public</span> : null}
          </div>
          {p.examples.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-200 p-5 text-sm text-slate-400">No public examples for this challenge.</div>
          ) : (
            <div className="space-y-4">
              {p.examples.map((sample, i) => (
                <div key={i} className="sample-block">
                  <div className="border-b border-black/5 px-4 py-2.5 font-mono text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">Example {i + 1}</div>
                  <div className="grid gap-px bg-black/5 lg:grid-cols-2">
                    <div className="bg-white p-4">
                      <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">Input</p>
                      <pre className="sample-pre">{sample.stdin}</pre>
                    </div>
                    <div className="bg-white p-4">
                      <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">Output</p>
                      <pre className="sample-pre">{sample.stdout}</pre>
                    </div>
                  </div>
                  {sample.explanation ? <p className="border-t border-black/5 bg-white px-4 py-3 text-sm leading-6 text-slate-600">{sample.explanation}</p> : null}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="grid gap-4 border-t border-black/5 pt-6 sm:grid-cols-2">
          <div>
            <h2 className="statement-h">Allowed languages</h2>
            <p className="text-sm font-semibold text-slate-700">{p.runtimes?.length ? p.runtimes.join(" · ") : "Standard languages"}</p>
          </div>
          <div>
            <h2 className="statement-h">Source</h2>
            {p.origin?.link ? (
              <a href={p.origin.link} target="_blank" rel="noreferrer" className="text-sm font-bold text-brand-600 hover:underline">{p.origin.provider ?? "External challenge source"} ↗</a>
            ) : <p className="text-sm text-slate-500">{p.origin?.provider ?? "Runline catalogue"}</p>}
          </div>
        </section>

        {p.derivedBudget ? <p className="text-[11px] text-slate-400">* CPU budget may be calibrated from a reference solution.</p> : null}
      </div>
    </article>
  );
}
