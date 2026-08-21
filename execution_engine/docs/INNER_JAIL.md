# Inner jail

The judge separates orchestration from the isolation mechanism. `execution_engine/core/sandbox.py` defines the boundary used for one test execution; `execution_engine/outer/` contains the current Linux primitives.

A single test follows this shape:

```text
create resource boundary
        |
spawn isolated process group
        |
attach to cgroup when available
        |
arm hard wall timeout
        |
wait/measure process
        |
classify resource/process result
        |
compare output
        |
clean sandbox state
```

## Production requirements

A hardened provider should enforce all of the following outside the worker process:

- CPU quota/accounting;
- memory limit;
- process-count limit;
- no network unless explicitly required;
- minimal read-only runtime filesystem;
- isolated writable work directory;
- hard wall-clock termination;
- deterministic cleanup after crashes/timeouts.

The development process adapter is useful for local testing but is not a security claim. The abstraction is intentionally compatible with nsjail, gVisor, Firecracker, or a pre-warmed sandbox pool.
