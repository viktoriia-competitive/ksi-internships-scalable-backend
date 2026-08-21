from __future__ import annotations

from typing import Any

VERDICTS = [
    "OK",
    "ACCEPTED",
    "WRONG_ANSWER",
    "TIME_LIMIT",
    "MEMORY_LIMIT",
    "RUNTIME_ERROR",
    "COMPILATION_ERROR",
    "INTERNAL_ERROR",
]


def _nonnegative_int(description: str) -> dict[str, Any]:
    return {"type": "integer", "minimum": 0, "description": description}


def run_result_schema() -> dict[str, Any]:
    fields: dict[str, Any] = {
        "status": {"type": "string", "enum": VERDICTS},
        "test_id": {"type": "string"},
        "exit_code": {"type": ["integer", "null"]},
        "cpu_ms": _nonnegative_int("CPU milliseconds consumed by this case."),
        "wall_ms": _nonnegative_int("Elapsed wall-clock milliseconds for this case."),
        "mem_kb": _nonnegative_int("Peak memory observed for this case, in KiB."),
        "message": {"type": "string"},
        "killed_by_wall": {"type": "boolean"},
        "killed_by_oom": {"type": "boolean"},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:runline:evaluation:case-result:v3",
        "title": "Runline case result",
        "type": "object",
        "additionalProperties": False,
        "properties": fields,
        "required": ["status", "exit_code", "cpu_ms", "wall_ms", "mem_kb"],
    }


def suite_request_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:runline:evaluation:suite-request:v3",
        "title": "Runline suite request",
        "type": "object",
        "additionalProperties": False,
        "$defs": {
            "limits": {
                "type": "object",
                "additionalProperties": False,
                "required": ["time_limit_ms", "memory_limit_mb"],
                "properties": {
                    "time_limit_ms": {"type": "integer", "minimum": 1},
                    "memory_limit_mb": {"type": "integer", "minimum": 1},
                    "wall_factor": {"type": "number", "exclusiveMinimum": 0, "default": 2.0},
                },
            }
        },
        "properties": {
            "run_key": {"type": "string", "minLength": 1},
            "runtime": {"type": "string", "minLength": 1},
            "source_path": {"type": "string", "minLength": 1},
            "tests_dir": {"type": "string", "minLength": 1},
            "work_dir": {"type": "string", "minLength": 1},
            "limits": {"$ref": "#/$defs/limits"},
            "checker": {"type": "string", "enum": ["token", "custom"], "default": "token"},
            "checker_path": {"type": ["string", "null"]},
            "stop_on_first_failure": {"type": "boolean", "default": True},
        },
        "required": ["run_key", "runtime", "source_path", "tests_dir", "work_dir", "limits"],
    }


def suite_result_schema() -> dict[str, Any]:
    aggregate_verdicts = [item for item in VERDICTS if item != "OK"]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:runline:evaluation:suite-result:v3",
        "title": "Runline suite result",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "status": {"type": "string", "enum": aggregate_verdicts},
            "tests_passed": _nonnegative_int("Number of accepted cases that executed."),
            "tests_total": _nonnegative_int("Number of complete input/output case pairs in the package."),
            "max_cpu_ms": _nonnegative_int("Largest per-case CPU observation."),
            "max_mem_kb": _nonnegative_int("Largest per-case memory observation."),
            "compile_message": {"type": "string"},
            "first_failure_message": {"type": "string"},
            "per_test": {
                "type": "array",
                "items": {"$ref": "run_result.schema.json"},
            },
        },
        "required": ["status", "tests_passed", "tests_total", "max_cpu_ms", "max_mem_kb"],
    }


SCHEMAS = {
    "run_result.schema.json": run_result_schema,
    "suite_request.schema.json": suite_request_schema,
    "suite_result.schema.json": suite_result_schema,
}
