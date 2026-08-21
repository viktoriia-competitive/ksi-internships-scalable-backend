"use client";

import { ChallengeStatement } from "@/components/challenge/ChallengeStatement";
import { AttemptComposer } from "@/features/challenge/AttemptComposer";
import { AttemptHistory } from "@/features/challenge/AttemptHistory";
import { useChallengeWorkspace } from "@/features/challenge/useChallengeWorkspace";
import type { ChallengeView } from "@/lib/contracts";

export function ChallengeWorkspace({ challenge }: { challenge: ChallengeView }) {
  const workspace = useChallengeWorkspace(challenge.key);

  return (
    <div className="challenge-detail-layout">
      <div className="challenge-detail-statement">
        <ChallengeStatement challenge={challenge} />
      </div>

      <aside className="challenge-detail-panel dark-surface">
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-3 sm:px-5">
          <div>
            <p className="font-mono text-[9px] font-bold uppercase tracking-[0.16em] text-brand-500">
              Workspace
            </p>
            <p className="mt-1 text-sm font-bold text-white">{challenge.shortCode}</p>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-slate-500">
            <span
              className={`h-1.5 w-1.5 rounded-full ${workspace.hasPending ? "bg-amber-400" : "bg-emerald-400"}`}
            />
            {workspace.hasPending ? "judge busy" : "ready"}
          </div>
        </div>

        <div className="flex border-b border-white/10" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={workspace.tab === "submit"}
            className={workspace.tab === "submit" ? "panel-tab panel-tab--active" : "panel-tab"}
            onClick={() => workspace.selectTab("submit")}
          >
            Code
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={workspace.tab === "history"}
            className={workspace.tab === "history" ? "panel-tab panel-tab--active" : "panel-tab"}
            onClick={() => workspace.selectTab("history")}
          >
            Attempts
            <span className="ml-1 font-mono text-[10px] text-slate-500">
              {workspace.attempts.length}
            </span>
          </button>
        </div>

        {workspace.error ? (
          <div className="border-b border-rose-500/20 bg-rose-500/10 px-4 py-2 text-xs text-rose-300">
            {workspace.error}
          </div>
        ) : null}

        <div className="min-h-0 flex-1 overflow-hidden">
          {workspace.tab === "submit" ? (
            <AttemptComposer challenge={challenge} onQueued={workspace.queueAttempt} />
          ) : (
            <AttemptHistory attempts={workspace.attempts} refreshing={workspace.refreshing} />
          )}
        </div>
      </aside>
    </div>
  );
}
