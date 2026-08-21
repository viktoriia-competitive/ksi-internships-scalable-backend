"""Translate storage-oriented domain snapshots into the public v2 contract."""

from __future__ import annotations

from control_plane.runtime.contracts.attempts import (
    AccountView,
    ArtifactView,
    AttemptView,
    CaseReport,
    ChallengeRef,
    EvaluationReport,
    FailureReport,
)
from control_plane.runtime.contracts.challenges import (
    ChallengeCard,
    ChallengePrompt,
    ChallengeView,
    EvaluationPolicy,
    ExampleCase,
    OriginRef,
    ResourceBudget,
    SourcePolicy,
)
from control_plane.runtime.core.entities import Challenge, Attempt, Account


_PUBLIC_PHASE = {
    "QUEUED": "waiting",
    "RUNNING": "executing",
    "ACCEPTED": "passed",
    "WRONG_ANSWER": "wrong_output",
    "TIME_LIMIT": "time_exceeded",
    "MEMORY_LIMIT": "memory_exceeded",
    "RUNTIME_ERROR": "runtime_failed",
    "COMPILATION_ERROR": "build_failed",
    "INTERNAL_ERROR": "platform_failed",
    "WRONG_EXTENSION": "artifact_rejected",
}


def public_phase(internal: str) -> str:
    return _PUBLIC_PHASE.get(internal, internal.casefold())


def internal_phase(public: str | None) -> str | None:
    if public is None:
        return None
    inverse = {value: key for key, value in _PUBLIC_PHASE.items()}
    return inverse.get(public.casefold(), public.upper())


def challenge_card(row: Challenge) -> ChallengeCard:
    details = row.profile or {}
    checker = ((details.get("evaluation") or {}).get("checker") or {})
    origin = details.get("origin") or {}
    budget = row.budget or {}
    return ChallengeCard(
        key=row.key,
        shortCode=row.short_code,
        name=row.name,
        level=row.level,
        score=row.score,
        acceptedCount=row.accepted_count,
        labels=list(row.labels or []),
        mode=row.mode,
        runtimes=list(row.runtimes or []),
        budget=ResourceBudget(
            cpuMillis=int(budget.get("cpuMillis", 2000)),
            memoryMiB=int(budget.get("memoryMiB", 256)),
        ),
        customChecker=(checker.get("kind") or "token") != "token",
        interactive=bool((details.get("evaluation") or {}).get("interactor")),
        origin=OriginRef(provider=origin.get("platform"), link=origin.get("url")),
    )


def challenge_view(row: Challenge) -> ChallengeView:
    card = challenge_card(row)
    details = row.profile or {}
    prompt = details.get("prompt") or {}
    suite = details.get("suite") or {}
    evaluation = details.get("evaluation") or {}
    checker = evaluation.get("checker") or {}
    artifact = details.get("artifact") or {}
    input_policy = details.get("input") or {}
    return ChallengeView(
        **card.model_dump(),
        derivedBudget=bool(details.get("budgetDerived", False)),
        prompt=ChallengePrompt(
            overview=prompt.get("overview") or "",
            inputContract=prompt.get("inputContract"),
            outputContract=prompt.get("outputContract"),
            interactionContract=prompt.get("interactionContract"),
            notes=prompt.get("notes"),
            markdown=prompt.get("markdown"),
        ),
        examples=[
            ExampleCase(
                stdin=sample.get("stdin", ""),
                stdout=sample.get("stdout", ""),
                explanation=sample.get("explanation"),
            )
            for sample in details.get("examples") or []
        ],
        evaluation=EvaluationPolicy(
            inputMode=input_policy.get("mode") or "stdio",
            inputFile=input_policy.get("inputFile"),
            outputFile=input_policy.get("outputFile"),
            checker=checker.get("kind") or "token",
            checkerOptions=checker.get("options"),
            testCount=suite.get("cases"),
            visibleTests=suite.get("visible"),
        ),
        sourcePolicy=SourcePolicy(
            artifactType=artifact.get("kind") or "source",
            extensions=list(artifact.get("extensions") or []),
            entrypoint=artifact.get("entrypoint"),
        ),
        referenceSolutions=len(details.get("references") or []),
    )


def _failure_report(data: object) -> FailureReport | None:
    if not isinstance(data, dict):
        return None
    return FailureReport(
        case=data.get("testId"),
        summary=str(data.get("message", "")),
        stdinExcerpt=str(data.get("inputPreview", "")),
        expectedExcerpt=str(data.get("expectedPreview", "")),
        actualExcerpt=str(data.get("actualPreview", "")),
        stderrExcerpt=str(data.get("stderrPreview", "")),
    )


def attempt_view(
    row: Attempt,
    *,
    include_report: bool = True,
    source_text: str | None = None,
    source_limit: int = 200_000,
) -> AttemptView:
    out = AttemptView(
        key=str(row.key),
        createdAt=row.created_at.isoformat().replace("+00:00", "Z"),
        challenge=ChallengeRef(key=row.challenge_key, shortCode=row.challenge_short_code, name=row.challenge_name),
        phase=public_phase(row.phase),
        runtime=row.runtime,
        artifact=ArtifactView(
            digest=row.artifact_ref,
            fileName=row.artifact_name,
            mediaType=row.media_type,
            bytes=row.artifact_bytes,
        ),
        actor=row.actor_handle,
    )
    if include_report and row.report:
        data = row.report
        out.report = EvaluationReport(
            passedCases=int(data.get("testsPassed", 0)),
            totalCases=int(data.get("testsTotal", 0)),
            peakCpuMillis=int(data.get("maxCpuMs", 0)),
            peakMemoryKiB=int(data.get("maxMemKb", 0)),
            compilerLog=str(data.get("compileMessage", "")),
            failureSummary=str(data.get("firstFailureMessage", "")),
            failure=_failure_report(data.get("failure")),
            cases=[
                CaseReport(
                    case=str(item.get("testId", "")),
                    outcome=public_phase(str(item.get("status", ""))),
                    cpuMillis=int(item.get("cpuMs", 0)),
                    memoryKiB=int(item.get("memKb", 0)),
                    note=str(item.get("message", "")),
                )
                for item in data.get("perTest") or []
            ],
        )
    if source_text is not None:
        raw = source_text.encode("utf-8")
        out.sourceText = raw[:source_limit].decode("utf-8", errors="replace")
        out.sourceTruncated = len(raw) > source_limit
    return out


def account_view(row: Account) -> AccountView:
    return AccountView(
        key=str(row.key),
        handle=row.handle,
        acceptedCount=row.accepted_count,
        completedChallenges=list(row.completed_challenge_keys or []),
    )
