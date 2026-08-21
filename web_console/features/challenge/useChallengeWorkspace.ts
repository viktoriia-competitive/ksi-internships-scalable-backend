"use client";

import { useCallback, useEffect, useMemo, useReducer, useRef } from "react";
import { browseChallengeAttempts, openAttempt } from "@/lib/api/attempts";
import type { Attempt, AttemptPhase, RuntimeName } from "@/lib/contracts";

export type WorkspaceTab = "submit" | "history";

type State = {
  tab: WorkspaceTab;
  attempts: Attempt[];
  error?: string;
  syncState: "idle" | "loading" | "refreshing";
};

type Action =
  | { type: "tab"; tab: WorkspaceTab }
  | { type: "sync-start"; visible: boolean }
  | { type: "sync-success"; attempts: Attempt[] }
  | { type: "sync-error"; message: string }
  | { type: "queued"; attempt: Attempt };

const FINISHED = new Set<AttemptPhase>([
  "passed", "wrong_output", "time_exceeded", "memory_exceeded", "runtime_failed",
  "build_failed", "platform_failed", "artifact_rejected",
]);

const initialState: State = { tab: "submit", attempts: [], syncState: "idle" };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "tab":
      return { ...state, tab: action.tab };
    case "sync-start":
      return { ...state, syncState: action.visible ? "refreshing" : state.syncState };
    case "sync-success":
      return { ...state, attempts: action.attempts, error: undefined, syncState: "idle" };
    case "sync-error":
      return { ...state, error: action.message, syncState: "idle" };
    case "queued":
      return {
        ...state,
        tab: "history",
        error: undefined,
        attempts: [action.attempt, ...state.attempts.filter((item) => item.key !== action.attempt.key)],
      };
  }
}

export interface ChallengeWorkspaceState {
  tab: WorkspaceTab;
  attempts: Attempt[];
  error?: string;
  refreshing: boolean;
  hasPending: boolean;
  selectTab(tab: WorkspaceTab): void;
  refresh(): Promise<void>;
  queueAttempt(runtime: RuntimeName, sourceText: string, artifactName?: string): Promise<void>;
}

export function useChallengeWorkspace(challengeKey: string): ChallengeWorkspaceState {
  const [state, dispatch] = useReducer(reducer, initialState);
  const generation = useRef(0);
  const hasPending = useMemo(
    () => state.attempts.some((attempt) => !FINISHED.has(attempt.phase)),
    [state.attempts],
  );

  const synchronize = useCallback(async (visible = true) => {
    const requestGeneration = ++generation.current;
    dispatch({ type: "sync-start", visible });
    try {
      const response = await browseChallengeAttempts(challengeKey, { page: 1, size: 40 });
      if (requestGeneration === generation.current) {
        dispatch({ type: "sync-success", attempts: response.entries });
      }
    } catch (reason) {
      if (requestGeneration === generation.current) {
        dispatch({ type: "sync-error", message: reason instanceof Error ? reason.message : String(reason) });
      }
    }
  }, [challengeKey]);

  useEffect(() => {
    void synchronize(true);
    return () => { generation.current += 1; };
  }, [synchronize]);

  useEffect(() => {
    if (!hasPending) return;
    let cancelled = false;
    let timer: number | undefined;
    const tick = async () => {
      await synchronize(false);
      if (!cancelled) timer = window.setTimeout(tick, 1800);
    };
    timer = window.setTimeout(tick, 1800);
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [hasPending, synchronize]);

  const queueAttempt = useCallback(async (runtime: RuntimeName, sourceText: string, artifactName?: string) => {
    const response = await openAttempt({ challengeKey, runtime, sourceText, artifactName });
    dispatch({ type: "queued", attempt: response.attempt });
  }, [challengeKey]);

  return {
    tab: state.tab,
    attempts: state.attempts,
    error: state.error,
    refreshing: state.syncState === "refreshing",
    hasPending,
    selectTab: (tab) => dispatch({ type: "tab", tab }),
    refresh: () => synchronize(true),
    queueAttempt,
  };
}
