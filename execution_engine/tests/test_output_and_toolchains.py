from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from execution_engine.outer.compare import token_compare, token_compare_files
from execution_engine.outer.compile import compile_source


@pytest.mark.parametrize(
    ("expected", "actual", "same"),
    [
        ("1 2\n3", "1\n2  3\n", True),
        ("", " \n\t", True),
        ("yes", "no", False),
        ("a b", "a b c", False),
    ],
)
def test_token_checker_compares_tokens_not_layout(expected: str, actual: str, same: bool) -> None:
    assert token_compare(expected, actual) is same


def test_file_checker_reads_utf8_outputs(tmp_path: Path) -> None:
    expected = tmp_path / "expected.txt"
    actual = tmp_path / "actual.txt"
    expected.write_text("alpha beta\n", encoding="utf-8")
    actual.write_text("alpha\n beta", encoding="utf-8")
    assert token_compare_files(expected, actual)


def test_python_toolchain_prepares_runnable_artifact(tmp_path: Path) -> None:
    source = tmp_path / "answer.py"
    source.write_text("print(42)\n", encoding="utf-8")
    result = compile_source("Python", source, tmp_path / "build")
    assert result.ok
    assert result.artifact_path and result.artifact_path.exists()
    assert result.run_argv[0] == "python3"


def test_unknown_toolchain_returns_compilation_failure(tmp_path: Path) -> None:
    source = tmp_path / "answer.txt"
    source.write_text("hello", encoding="utf-8")
    result = compile_source("Whitespace++", source, tmp_path / "build")
    assert not result.ok
    assert result.compiler_stderr


def test_cpp_toolchain_when_compiler_is_installed(tmp_path: Path) -> None:
    if shutil.which("g++") is None:
        pytest.skip("g++ is not installed")
    source = tmp_path / "main.cpp"
    source.write_text("#include <iostream>\nint main(){std::cout << 7 << '\\n';}\n", encoding="utf-8")
    result = compile_source("C++", source, tmp_path / "build")
    assert result.ok, result.compiler_stderr
    assert Path(result.run_argv[0]).is_file()
