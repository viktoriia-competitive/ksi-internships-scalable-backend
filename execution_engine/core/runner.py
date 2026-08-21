from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from execution_engine.outer.compile import CompileResult, compile_source


@dataclass(frozen=True, slots=True)
class PreparedProgram:
    argv: Sequence[str]
    compile_result: CompileResult


class ProgramRunner:
    def prepare(self, language: str, source_path: Path, work_dir: Path) -> PreparedProgram:
        result = compile_source(language, source_path, work_dir)
        return PreparedProgram(argv=tuple(result.run_argv), compile_result=result)
