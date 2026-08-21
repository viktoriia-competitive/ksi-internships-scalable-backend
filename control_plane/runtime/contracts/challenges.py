"""Public HTTP contracts for the challenge catalogue."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ResourceBudget(BaseModel):
    cpuMillis: int = Field(ge=1)
    memoryMiB: int = Field(ge=1)


class OriginRef(BaseModel):
    provider: str | None = None
    link: str | None = None


class ChallengeCard(BaseModel):
    key: str
    shortCode: str
    name: str
    level: str
    score: int | None = None
    acceptedCount: int = 0
    labels: list[str] = Field(default_factory=list)
    mode: str = "stdio"
    runtimes: list[str] = Field(default_factory=list)
    budget: ResourceBudget
    customChecker: bool = False
    interactive: bool = False
    origin: OriginRef | None = None


class ExampleCase(BaseModel):
    stdin: str = ""
    stdout: str = ""
    explanation: str | None = None


class ChallengePrompt(BaseModel):
    overview: str = ""
    inputContract: str | None = None
    outputContract: str | None = None
    interactionContract: str | None = None
    notes: str | None = None
    markdown: str | None = None


class EvaluationPolicy(BaseModel):
    inputMode: str = "stdio"
    inputFile: str | None = None
    outputFile: str | None = None
    checker: str = "tokens"
    checkerOptions: dict[str, Any] | None = None
    testCount: int | None = None
    visibleTests: int | None = None


class SourcePolicy(BaseModel):
    artifactType: str = "source"
    extensions: list[str] = Field(default_factory=list)
    entrypoint: str | None = None


class ChallengeView(ChallengeCard):
    derivedBudget: bool = False
    prompt: ChallengePrompt = Field(default_factory=ChallengePrompt)
    examples: list[ExampleCase] = Field(default_factory=list)
    evaluation: EvaluationPolicy = Field(default_factory=EvaluationPolicy)
    sourcePolicy: SourcePolicy = Field(default_factory=SourcePolicy)
    referenceSolutions: int = 0


class PageInfo(BaseModel):
    index: int
    size: int
    totalEntries: int
    totalPages: int


class ChallengeCollection(BaseModel):
    entries: list[ChallengeCard]
    pageInfo: PageInfo


ChallengeOrder = Literal["shortCode", "name", "level", "acceptedCount", "key", "score", "mode"]
