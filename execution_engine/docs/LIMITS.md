# Resource budgets

Every `challenge.json` declares a per-case budget:

```json
{
  "budget": {
    "cpuMillis": 1000,
    "memoryMiB": 64,
    "derived": false
  }
}
```

CPU and memory allowances reset for each paired `.in`/`.out` case. The suite
report records peak observations, but those aggregates are diagnostics rather
than a second global limit. Compilation uses its own timeout.

| Observation | Verdict |
|---|---|
| Kernel OOM or enforced memory excess | `MEMORY_LIMIT` |
| Wall deadline or enforced CPU excess | `TIME_LIMIT` |
| Signal, unknown exit, or non-zero exit | `RUNTIME_ERROR` |
| Successful process and accepted output | `ACCEPTED` |
| Successful process and rejected output | `WRONG_ANSWER` |

The wall deadline defaults to a multiple of `cpuMillis`; it stops sleeping or
blocked programs even when they consume little CPU. Enforcement metadata remains
part of the process observation so development mode does not misrepresent a
best-effort measurement as a kernel-enforced boundary.
