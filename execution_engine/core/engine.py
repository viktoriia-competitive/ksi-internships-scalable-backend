from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

from execution_engine.core.models import SuiteResult
from execution_engine.core.bundle import ChallengeBundle, load_challenge_bundle
from execution_engine.core.runner import ProgramRunner
from execution_engine.core.sandbox import ProcessSandbox, SandboxProvider
from execution_engine.core.session import SuiteSession
from execution_engine.core.verdicts import VerdictPolicy

_LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C++",
    ".java": "Java",
    ".rs": "Rust",
    ".go": "Go",
    ".sh": "Bash",
    ".sql": "SQL",
}


class EvaluationCoordinator:
    """Stable facade that assembles the v2 suite session."""

    def __init__(self, *, sandbox: SandboxProvider, runner: ProgramRunner | None = None) -> None:
        self._sandbox = sandbox
        self._runner = runner or ProgramRunner()
        self._verdicts = VerdictPolicy()

    @property
    def sandbox(self) -> SandboxProvider:
        return self._sandbox

    @property
    def runner(self) -> ProgramRunner:
        return self._runner

    def evaluate(
        self,
        bundle: ChallengeBundle,
        source_path: Path,
        *,
        runtime: str,
        run_key: str,
        work_dir: Path,
        stop_on_first_failure: bool = True,
    ) -> SuiteResult:
        session = SuiteSession(
            bundle=bundle,
            source_path=Path(source_path),
            runtime=runtime,
            run_key=run_key,
            work_dir=Path(work_dir),
            sandbox=self._sandbox,
            runner=self._runner,
            verdict_policy=self._verdicts,
        )
        return session.execute(stop_after_failure=stop_on_first_failure)


def evaluate_bundle(
    bundle_dir: Path,
    source_path: Path,
    *,
    runtime: str | None = None,
    run_key: str | None = None,
    work_dir: Path | None = None,
    stop_on_first_failure: bool = True,
    use_cgroup: bool = True,
    keep_work_dir: bool = False,
) -> SuiteResult:
    bundle = load_challenge_bundle(Path(bundle_dir))
    original_source = Path(source_path).resolve()
    selected_runtime = runtime or _infer_runtime(original_source, bundle)
    evaluation_key = run_key or f"run-{uuid.uuid4().hex[:12]}"

    temporary: tempfile.TemporaryDirectory[str] | None = None
    if work_dir is None:
        temporary = tempfile.TemporaryDirectory(prefix=f"runline-{evaluation_key}-")
        workspace = Path(temporary.name)
    else:
        workspace = Path(work_dir)
        workspace.mkdir(parents=True, exist_ok=True)

    try:
        staged_source = workspace / original_source.name
        if staged_source.resolve() != original_source:
            shutil.copy2(original_source, staged_source)
        coordinator = EvaluationCoordinator(sandbox=ProcessSandbox(use_cgroup=use_cgroup))
        return coordinator.evaluate(
            bundle,
            staged_source,
            runtime=selected_runtime,
            run_key=evaluation_key,
            work_dir=workspace,
            stop_on_first_failure=stop_on_first_failure,
        )
    finally:
        if temporary is not None and not keep_work_dir:
            temporary.cleanup()


def _infer_runtime(source: Path, bundle: ChallengeBundle) -> str:
    known = _LANGUAGE_BY_SUFFIX.get(source.suffix.casefold())
    if known:
        return known
    configured = bundle.metadata.get("runtimes") or []
    return str(configured[0]) if configured else "Python"
