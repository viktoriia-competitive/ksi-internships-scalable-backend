# Engine usage

From the repository root, evaluate a fixture directly:

```bash
export PYTHONPATH=.
python -m execution_engine.worker.cli \
  --bundle execution_engine/fixtures/sum_pair \
  --source execution_engine/fixtures/sum_pair/main.py \
  --runtime Python \
  --no-cgroup
```

`--out` writes the structured result, while `--all-tests` continues after the
first failing case. This command is for smoke tests and debugging; the API process
never invokes it.

Normal application flow starts with `POST /control/v2/attempts`, commits an
attempt plus outbox command, delivers that command through Redis Streams, and
runs `python -m control_plane.runtime.worker.main`. The worker invokes
`execution_engine.core.engine.evaluate_bundle` and persists the terminal report
before acknowledging delivery.

Without writable cgroup v2, local mode retains a wall-clock watchdog but cannot
claim production-strength CPU or memory enforcement.
