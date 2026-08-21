"use client";

import { useDeferredValue, useEffect, useMemo, useReducer, type ReactNode } from "react";
import { ChallengeTable } from "@/features/challenges/ChallengeTable";
import { browseChallenges } from "@/lib/api/challenges";
import type {
  ChallengeCollection,
  ChallengeLevel,
  ChallengeMode,
  ChallengeOrder,
} from "@/lib/contracts";

type FilterState = {
  search: string;
  level: ChallengeLevel | "all";
  label: string;
  mode: ChallengeMode | "all";
  orderBy: ChallengeOrder;
  direction: "asc" | "desc";
  page: number;
  size: number;
};

type ExplorerState = {
  filter: FilterState;
  catalogue: ChallengeCollection | null;
  requestState: "loading" | "ready" | "failed";
  error?: string;
};

type ExplorerAction =
  | { type: "change-filter"; patch: Partial<FilterState>; keepPage?: boolean }
  | { type: "clear-filter" }
  | { type: "request-started" }
  | { type: "request-succeeded"; catalogue: ChallengeCollection }
  | { type: "request-failed"; message: string };

const INITIAL_FILTER: FilterState = {
  search: "",
  level: "all",
  label: "",
  mode: "all",
  orderBy: "shortCode",
  direction: "asc",
  page: 1,
  size: 40,
};

const MODES: Array<ChallengeMode | "all"> = ["all", "stdio", "interactive", "library", "sql", "bash", "archive"];

function evolve(state: ExplorerState, action: ExplorerAction): ExplorerState {
  switch (action.type) {
    case "change-filter":
      return {
        ...state,
        filter: {
          ...state.filter,
          ...action.patch,
          page: action.keepPage ? (action.patch.page ?? state.filter.page) : 1,
        },
      };
    case "clear-filter":
      return { ...state, filter: INITIAL_FILTER };
    case "request-started":
      return { ...state, requestState: "loading" };
    case "request-succeeded":
      return { ...state, catalogue: action.catalogue, requestState: "ready", error: undefined };
    case "request-failed":
      return { ...state, requestState: "failed", error: action.message };
  }
}

export function ChallengeExplorer() {
  const [state, dispatch] = useReducer(evolve, {
    filter: INITIAL_FILTER,
    catalogue: null,
    requestState: "loading",
  });
  const delayedSearch = useDeferredValue(state.filter.search.trim());
  const delayedLabel = useDeferredValue(state.filter.label.trim());

  useEffect(() => {
    let current = true;
    dispatch({ type: "request-started" });
    void browseChallenges({
      search: delayedSearch,
      level: state.filter.level,
      label: delayedLabel || "all",
      mode: state.filter.mode,
      orderBy: state.filter.orderBy,
      direction: state.filter.direction,
      page: state.filter.page,
      size: state.filter.size,
    })
      .then((catalogue) => current && dispatch({ type: "request-succeeded", catalogue }))
      .catch((error) => {
        if (current) dispatch({ type: "request-failed", message: error instanceof Error ? error.message : String(error) });
      });
    return () => { current = false; };
  }, [
    delayedLabel,
    delayedSearch,
    state.filter.direction,
    state.filter.level,
    state.filter.mode,
    state.filter.orderBy,
    state.filter.page,
    state.filter.size,
  ]);

  const page = state.catalogue?.pageInfo;
  const visibleRange = useMemo(() => {
    if (!page || page.totalEntries === 0) return "0";
    const start = (page.index - 1) * page.size + 1;
    const shown = state.catalogue?.entries.length ?? 0;
    return `${start}–${Math.min(start + shown - 1, page.totalEntries)}`;
  }, [page, state.catalogue]);
  const loading = state.requestState === "loading";
  const change = (patch: Partial<FilterState>, keepPage = false) =>
    dispatch({ type: "change-filter", patch, keepPage });

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="eyebrow">Challenge catalogue</p>
          <h1 className="page-title mt-2">Choose an execution challenge.</h1>
          <p className="page-copy mt-2">Search the catalogue by level, runtime mode, label, or title.</p>
        </div>
        <div className="rounded-xl border border-black/10 bg-white px-4 py-3 text-right">
          <div className="font-mono text-xl font-black text-ink-950">{(page?.totalEntries ?? 0).toLocaleString()}</div>
          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">available</div>
        </div>
      </header>

      {state.error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{state.error}</div> : null}

      <section className="surface overflow-hidden">
        <div className="border-b border-black/5 bg-ink-950 p-4 text-white sm:p-5">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(260px,2fr)_1fr_1fr_1fr]">
            <FilterField label="Search">
              <input className="field !border-white/10 !bg-white/10 !text-white" type="search" value={state.filter.search} onChange={(event) => change({ search: event.target.value })} placeholder="Code, name, or keyword" />
            </FilterField>
            <FilterField label="Level">
              <select className="field !border-white/10 !bg-ink-800 !text-white" value={state.filter.level} onChange={(event) => change({ level: event.target.value as FilterState["level"] })}>
                <option value="all">All levels</option><option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option>
              </select>
            </FilterField>
            <FilterField label="Mode">
              <select className="field !border-white/10 !bg-ink-800 !text-white" value={state.filter.mode} onChange={(event) => change({ mode: event.target.value as FilterState["mode"] })}>
                {MODES.map((mode) => <option key={mode} value={mode}>{mode === "all" ? "All modes" : mode}</option>)}
              </select>
            </FilterField>
            <FilterField label="Label">
              <input className="field !border-white/10 !bg-white/10 !text-white" value={state.filter.label} onChange={(event) => change({ label: event.target.value })} placeholder="e.g. graphs" />
            </FilterField>
          </div>
        </div>

        <div className="flex flex-col gap-3 border-b border-black/5 px-5 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <span className="text-xs text-slate-500">{loading ? "Refreshing…" : `Showing ${visibleRange} of ${(page?.totalEntries ?? 0).toLocaleString()}`}</span>
          <div className="flex flex-wrap items-center gap-2">
            <select className="h-8 rounded-lg border border-slate-200 bg-white px-2 text-xs font-semibold text-slate-600" value={state.filter.orderBy} onChange={(event) => change({ orderBy: event.target.value as ChallengeOrder })}>
              <option value="shortCode">Code</option><option value="name">Name</option><option value="level">Level</option><option value="score">Score</option><option value="acceptedCount">Accepted</option>
            </select>
            <button type="button" className="h-8 rounded-lg border border-slate-200 bg-white px-3 text-xs font-bold text-slate-600" onClick={() => change({ direction: state.filter.direction === "asc" ? "desc" : "asc" })}>{state.filter.direction === "asc" ? "↑ Asc" : "↓ Desc"}</button>
            <button type="button" className="h-8 rounded-lg px-3 text-xs font-bold text-brand-600" onClick={() => dispatch({ type: "clear-filter" })}>Clear</button>
          </div>
        </div>

        <ChallengeTable items={state.catalogue?.entries ?? []} />

        <nav className="flex items-center justify-between border-t border-black/5 px-5 py-4 sm:px-6" aria-label="Challenge pages">
          <button className="btn-secondary" type="button" disabled={loading || !page || page.index <= 1} onClick={() => change({ page: Math.max(1, (page?.index ?? 1) - 1) }, true)}>← Previous</button>
          <span className="font-mono text-xs text-slate-400">{page?.index ?? 1} / {page?.totalPages ?? 1}</span>
          <button className="btn-primary" type="button" disabled={loading || !page || page.index >= page.totalPages} onClick={() => change({ page: (page?.index ?? 1) + 1 }, true)}>Next →</button>
        </nav>
      </section>
    </div>
  );
}

function FilterField({ label, children }: { label: string; children: ReactNode }) {
  return <label className="space-y-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500">{label}{children}</label>;
}
