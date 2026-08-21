"""Public HTTP contracts for source attempts and account projections."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ArtifactView(BaseModel):
    digest: str
    fileName: str
    mediaType: str
    bytes: int


class ChallengeRef(BaseModel):
    key: str
    shortCode: str
    name: str


class CaseReport(BaseModel):
    case: str = ""
    outcome: str = ""
    cpuMillis: int = 0
    memoryKiB: int = 0
    note: str = ""


class FailureReport(BaseModel):
    case: str | None = None
    summary: str = ""
    stdinExcerpt: str = ""
    expectedExcerpt: str = ""
    actualExcerpt: str = ""
    stderrExcerpt: str = ""


class EvaluationReport(BaseModel):
    passedCases: int = 0
    totalCases: int = 0
    peakCpuMillis: int = 0
    peakMemoryKiB: int = 0
    compilerLog: str = ""
    failureSummary: str = ""
    failure: FailureReport | None = None
    cases: list[CaseReport] = Field(default_factory=list)


class AttemptView(BaseModel):
    key: str
    createdAt: str
    challenge: ChallengeRef
    phase: str
    runtime: str
    artifact: ArtifactView
    actor: str | None = None
    report: EvaluationReport | None = None
    sourceText: str | None = None
    sourceTruncated: bool = False


class PageInfo(BaseModel):
    index: int
    size: int
    totalEntries: int
    totalPages: int


class AttemptCollection(BaseModel):
    entries: list[AttemptView]
    pageInfo: PageInfo


class OpenAttemptRequest(BaseModel):
    challengeKey: str = Field(min_length=1, max_length=128)
    runtime: str = Field(min_length=1, max_length=32)
    sourceText: str = Field(min_length=1, max_length=524_288)
    artifactName: str | None = Field(default=None, max_length=255)
    mediaType: str | None = Field(default=None, max_length=128)


class AttemptLinks(BaseModel):
    self: str
    events: str
    source: str


class OpenAttemptResponse(BaseModel):
    attempt: AttemptView
    links: AttemptLinks


class AccountView(BaseModel):
    key: str
    handle: str
    acceptedCount: int = 0
    completedChallenges: list[str] = Field(default_factory=list)


class LifecycleEventView(BaseModel):
    index: int
    event: str
    recordedAt: str
    runKey: str
    deliveryKey: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class LifecycleTimeline(BaseModel):
    entries: list[LifecycleEventView]
