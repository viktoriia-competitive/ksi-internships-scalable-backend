# Decision 003 — isolate platform mechanics

Status: accepted.

Process launch, cgroup access, deadlines, filesystem exposure, and wait-status
accounting belong behind `SandboxProvider`. Suite orchestration sees only a
process request and a measured observation.

The checked-in Linux provider supports development and capability tests. A
production provider may use a stronger container or micro-VM boundary without
changing challenge loading, output evaluation, control-plane persistence, or the
public API.
