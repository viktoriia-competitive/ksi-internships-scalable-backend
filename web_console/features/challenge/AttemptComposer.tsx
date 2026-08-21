"use client";

import { useMemo, useReducer, useRef, type ChangeEvent, type FormEvent } from "react";
import { CodeEditor } from "@/components/challenge/CodeEditor";
import type { ChallengeView, RuntimeName } from "@/lib/contracts";
import { RUNTIMES, isRuntimeName } from "@/lib/contracts";

const MAX_UPLOAD_BYTES = 512 * 1024;

const RUNTIME_PRESETS: Record<RuntimeName, { extension: string; starter: string }> = {
  Python: { extension: "py", starter: 'import sys\n\ndef solve() -> None:\n    pass\n\nif __name__ == "__main__":\n    solve()\n' },
  "C++": { extension: "cpp", starter: "#include <iostream>\n\nint main() {\n    std::ios::sync_with_stdio(false);\n    std::cin.tie(nullptr);\n    return 0;\n}\n" },
  Java: { extension: "java", starter: "public class Main {\n    public static void main(String[] args) throws Exception {\n    }\n}\n" },
  Rust: { extension: "rs", starter: "fn main() {\n}\n" },
  Go: { extension: "go", starter: "package main\n\nfunc main() {\n}\n" },
  Bash: { extension: "sh", starter: "#!/usr/bin/env bash\nset -euo pipefail\n" },
  SQL: { extension: "sql", starter: "SELECT 1;\n" },
};

const RUNTIME_BY_EXTENSION = new Map<string, RuntimeName>([
  ["py", "Python"], ["cpp", "C++"], ["cc", "C++"], ["cxx", "C++"],
  ["java", "Java"], ["rs", "Rust"], ["go", "Go"], ["sh", "Bash"], ["sql", "SQL"],
]);

type DraftState = {
  runtime: RuntimeName;
  sourceText: string;
  artifactName?: string;
  notice?: string;
  submitting: boolean;
};

type DraftAction =
  | { type: "runtime"; runtime: RuntimeName }
  | { type: "sourceText"; sourceText: string }
  | { type: "file"; sourceText: string; artifactName: string; runtime?: RuntimeName }
  | { type: "notice"; notice?: string }
  | { type: "submitting"; value: boolean };

function draftReducer(state: DraftState, action: DraftAction): DraftState {
  switch (action.type) {
    case "runtime": {
      const oldStarter = RUNTIME_PRESETS[state.runtime].starter;
      const preserveSource = state.sourceText !== oldStarter;
      return {
        ...state,
        runtime: action.runtime,
        sourceText: preserveSource ? state.sourceText : RUNTIME_PRESETS[action.runtime].starter,
      };
    }
    case "sourceText":
      return { ...state, sourceText: action.sourceText };
    case "file":
      return {
        ...state,
        sourceText: action.sourceText,
        artifactName: action.artifactName,
        runtime: action.runtime ?? state.runtime,
        notice: `Imported ${action.artifactName}`,
      };
    case "notice":
      return { ...state, notice: action.notice };
    case "submitting":
      return { ...state, submitting: action.value };
  }
}

function runtimesFor(challenge: ChallengeView): RuntimeName[] {
  const configured = (challenge.runtimes ?? []).filter(isRuntimeName);
  if (configured.length) return configured;
  return RUNTIMES.filter((runtime) => runtime !== "SQL" && runtime !== "Bash");
}

export function AttemptComposer({
  challenge,
  onQueued,
}: {
  challenge: ChallengeView;
  onQueued: (runtime: RuntimeName, sourceText: string, artifactName?: string) => Promise<void>;
}) {
  const runtimes = useMemo(() => runtimesFor(challenge), [challenge]);
  const fallback = runtimes[0] ?? "Python";
  const [draft, dispatch] = useReducer(draftReducer, {
    runtime: fallback,
    sourceText: RUNTIME_PRESETS[fallback].starter,
    submitting: false,
  });
  const fileInput = useRef<HTMLInputElement>(null);

  async function attachFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.item(0);
    event.target.value = "";
    if (!file) return;
    if (file.size > MAX_UPLOAD_BYTES) {
      dispatch({ type: "notice", notice: "File is larger than 512 KiB." });
      return;
    }

    try {
      const sourceText = await file.text();
      const extension = file.name.includes(".") ? file.name.split(".").pop()?.toLowerCase() : undefined;
      const detected = extension ? RUNTIME_BY_EXTENSION.get(extension) : undefined;
      dispatch({
        type: "file",
        sourceText,
        artifactName: file.name,
        runtime: detected && runtimes.includes(detected) ? detected : undefined,
      });
    } catch {
      dispatch({ type: "notice", notice: "Could not read the selected file." });
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.sourceText.trim()) {
      dispatch({ type: "notice", notice: "Add source code before submitting." });
      return;
    }

    dispatch({ type: "submitting", value: true });
    dispatch({ type: "notice", notice: undefined });
    try {
      await onQueued(draft.runtime, draft.sourceText, draft.artifactName);
      dispatch({ type: "notice", notice: "Attempt queued for judging." });
    } catch (error) {
      dispatch({ type: "notice", notice: error instanceof Error ? error.message : String(error) });
    } finally {
      dispatch({ type: "submitting", value: false });
    }
  }

  const displayName = draft.artifactName ?? `main.${RUNTIME_PRESETS[draft.runtime].extension}`;

  return (
    <form className="submit-form" onSubmit={submit}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="min-w-0 flex-1 space-y-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500">
          Runtime
          <select
            className="field !border-white/10 !bg-ink-800 !text-white focus:!border-brand-500 focus:!ring-brand-500/10"
            value={draft.runtime}
            onChange={(event) => dispatch({ type: "runtime", runtime: event.target.value as RuntimeName })}
          >
            {runtimes.map((runtime) => <option key={runtime} value={runtime}>{runtime}</option>)}
          </select>
        </label>
        <input ref={fileInput} className="hidden" type="file" onChange={attachFile} />
        <button
          type="button"
          className="inline-flex h-10 items-center justify-center rounded-xl border border-white/10 px-4 text-xs font-bold text-slate-300 transition hover:bg-white/10 hover:text-white"
          onClick={() => fileInput.current?.click()}
        >
          Open source file
        </button>
      </div>

      <section className="submit-editor-block" aria-label="Attempt editor">
        <div className="mb-2 flex items-center justify-between gap-3">
          <span className="font-mono text-[10px] text-slate-500">{displayName}</span>
          <span className="font-mono text-[10px] text-slate-600">{draft.sourceText.length.toLocaleString()} chars</span>
        </div>
        <CodeEditor
          runtime={draft.runtime}
          value={draft.sourceText}
          onChange={(sourceText) => dispatch({ type: "sourceText", sourceText })}
        />
      </section>

      <footer className="flex flex-col gap-3 border-t border-white/10 pt-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-h-5 text-xs text-slate-400">
          {draft.notice ?? "The worker evaluates each test in an isolated execution boundary."}
        </div>
        <button className="btn-accent shrink-0" type="submit" disabled={draft.submitting}>
          {draft.submitting ? "Queueing…" : "Run attempt →"}
        </button>
      </footer>
    </form>
  );
}
