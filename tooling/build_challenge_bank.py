from __future__ import annotations

import json
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
CHALLENGES_ROOT = ROOT / "challenge_bank" / "challenges"
RNG = random.Random(20260818)


@dataclass(frozen=True)
class ChallengeBlueprint:
    slug: str
    short_code: str
    name: str
    level: str
    score: int
    labels: tuple[str, ...]
    overview: str
    input_contract: str
    output_contract: str
    reference_source: str
    case_factory: Callable[[], list[str]]
    examples: tuple[str, ...]
    checker_kind: str = "token"
    checker_source: str | None = None
    notes: str | None = None
    cpu_millis: int = 2000
    memory_mib: int = 128


def solve_with_model(source: str, input_text: str) -> str:
    namespace: dict[str, object] = {"__name__": "runline_model"}
    exec(compile(source, "<model>", "exec"), namespace)
    solve = namespace["solve"]
    return str(solve(input_text)).rstrip() + "\n"


def random_ints(n: int, lo: int, hi: int) -> list[int]:
    return [RNG.randint(lo, hi) for _ in range(n)]


def signal_window_cases() -> list[str]:
    cases = ["1 1\n5\n", "5 3\n1 2 3 4 5\n", "6 2\n-5 -2 -7 -1 -3 -4\n"]
    for _ in range(17):
        n = RNG.randint(2, 80)
        k = RNG.randint(1, n)
        values = random_ints(n, -100, 150)
        cases.append(f"{n} {k}\n" + " ".join(map(str, values)) + "\n")
    return cases


def gap_monitor_cases() -> list[str]:
    cases = ["2\n10 15\n", "5\n0 4 4 9 21\n"]
    for _ in range(18):
        n = RNG.randint(2, 80)
        cur = RNG.randint(0, 10)
        values = [cur]
        for _ in range(n - 1):
            cur += RNG.randint(0, 30)
            values.append(cur)
        cases.append(f"{n}\n" + " ".join(map(str, values)) + "\n")
    return cases


def batch_dedup_cases() -> list[str]:
    cases = ["6\na b a c b d\n", "1\nsolo\n"]
    alphabet = [f"key{i}" for i in range(20)]
    for _ in range(18):
        n = RNG.randint(1, 100)
        seq = [RNG.choice(alphabet) for _ in range(n)]
        cases.append(f"{n}\n" + " ".join(seq) + "\n")
    return cases


def latency_bucket_cases() -> list[str]:
    cases = ["3 7\n50 100 250\n10 50 51 100 101 250 999\n"]
    for _ in range(19):
        b = RNG.randint(1, 8)
        thresholds = sorted(RNG.sample(range(5, 500), b))
        n = RNG.randint(1, 120)
        values = random_ints(n, 0, 700)
        cases.append(f"{b} {n}\n" + " ".join(map(str, thresholds)) + "\n" + " ".join(map(str, values)) + "\n")
    return cases


def retry_schedule_cases() -> list[str]:
    cases = ["5 2 20 5\n", "3 3 100 1\n"]
    for _ in range(18):
        initial = RNG.randint(1, 20)
        factor = RNG.randint(1, 5)
        cap = RNG.randint(initial, 200)
        attempts = RNG.randint(1, 15)
        cases.append(f"{initial} {factor} {cap} {attempts}\n")
    return cases


def event_merge_cases() -> list[str]:
    cases = ["3\n3 1 4 8\n2 1 7\n4 2 2 9 10\n"]
    for _ in range(19):
        k = RNG.randint(1, 6)
        lines = [str(k)]
        for _ in range(k):
            n = RNG.randint(0, 20)
            values = sorted(random_ints(n, -20, 80))
            lines.append(str(n) + ((" " + " ".join(map(str, values))) if values else ""))
        cases.append("\n".join(lines) + "\n")
    return cases


def cache_expiry_cases() -> list[str]:
    cases = [
        "7\n0 SET a 5\n2 GET a\n5 GET a\n6 SET a 2\n7 GET a\n8 GET a\n9 GET b\n",
    ]
    keys = ["a", "b", "c", "user", "token"]
    for _ in range(19):
        q = RNG.randint(10, 70)
        t = 0
        lines = [str(q)]
        for _ in range(q):
            t += RNG.randint(0, 3)
            key = RNG.choice(keys)
            if RNG.random() < 0.45:
                ttl = RNG.randint(1, 12)
                lines.append(f"{t} SET {key} {ttl}")
            else:
                lines.append(f"{t} GET {key}")
        cases.append("\n".join(lines) + "\n")
    return cases


def shard_capacity_cases() -> list[str]:
    cases = ["5 2\n7 2 5 10 8\n", "4 4\n3 1 9 2\n"]
    for _ in range(18):
        n = RNG.randint(1, 50)
        workers = RNG.randint(1, n)
        weights = random_ints(n, 1, 80)
        cases.append(f"{n} {workers}\n" + " ".join(map(str, weights)) + "\n")
    return cases


def dependency_wave_cases() -> list[str]:
    cases = ["5 4\n1 3\n2 3\n3 4\n3 5\n", "3 3\n1 2\n2 3\n3 1\n"]
    for _ in range(18):
        n = RNG.randint(2, 35)
        make_cycle = RNG.random() < 0.2
        order = list(range(1, n + 1))
        RNG.shuffle(order)
        pos = {v: i for i, v in enumerate(order)}
        edges: set[tuple[int, int]] = set()
        for _ in range(RNG.randint(n - 1, min(n * 3, n * (n - 1) // 2))):
            a, b = RNG.sample(range(1, n + 1), 2)
            if pos[a] < pos[b]:
                edges.add((a, b))
            else:
                edges.add((b, a))
        if make_cycle and n >= 3:
            a, b, c = RNG.sample(range(1, n + 1), 3)
            edges.update({(a, b), (b, c), (c, a)})
        lines = [f"{n} {len(edges)}"] + [f"{a} {b}" for a, b in sorted(edges)]
        cases.append("\n".join(lines) + "\n")
    return cases


def quorum_window_cases() -> list[str]:
    cases = ["8 3 2\n1 1\n2 2\n3 3\n4 1\n6 2\n7 3\n9 1\n12 2\n"]
    for _ in range(19):
        services = RNG.randint(1, 6)
        quota = RNG.randint(1, 4)
        n = RNG.randint(services * quota, 100)
        t = 0
        events: list[tuple[int, int]] = []
        for _ in range(n):
            t += RNG.randint(0, 5)
            events.append((t, RNG.randint(1, services)))
        # Roughly half the cases are guaranteed feasible.
        if RNG.random() < 0.5:
            t += 1
            for service in range(1, services + 1):
                for _ in range(quota):
                    events.append((t, service))
                    t += RNG.randint(0, 1)
            events.sort()
        lines = [f"{len(events)} {services} {quota}"] + [f"{ts} {svc}" for ts, svc in events]
        cases.append("\n".join(lines) + "\n")
    return cases


def nearest_pair_cases() -> list[str]:
    cases = ["3\n10 1 8 3 4 20\n", "1\n5 9\n"]
    for _ in range(18):
        pairs = RNG.randint(1, 20)
        values = RNG.sample(range(-300, 301), pairs * 2)
        cases.append(f"{pairs}\n" + " ".join(map(str, values)) + "\n")
    return cases


MODELS = {
"signal_window": '''def solve(data: str) -> str:\n    it = iter(map(int, data.split()))\n    n, k = next(it), next(it)\n    values = [next(it) for _ in range(n)]\n    current = sum(values[:k])\n    best = current\n    for i in range(k, n):\n        current += values[i] - values[i-k]\n        best = max(best, current)\n    return str(best)\n''',
"gap_monitor": '''def solve(data: str) -> str:\n    values = list(map(int, data.split()))\n    n = values[0]\n    ts = values[1:1+n]\n    best_gap = -1\n    best_end = 2\n    for i in range(1, n):\n        gap = ts[i] - ts[i-1]\n        if gap > best_gap:\n            best_gap, best_end = gap, i + 1\n    return f"{best_gap} {best_end}"\n''',
"batch_dedup": '''def solve(data: str) -> str:\n    parts = data.split()\n    n = int(parts[0])\n    seen = set()\n    out = []\n    for token in parts[1:1+n]:\n        if token not in seen:\n            seen.add(token)\n            out.append(token)\n    return str(len(out)) + "\\n" + " ".join(out)\n''',
"latency_buckets": '''def solve(data: str) -> str:\n    nums = list(map(int, data.split()))\n    b, n = nums[0], nums[1]\n    limits = nums[2:2+b]\n    values = nums[2+b:2+b+n]\n    counts = [0] * (b + 1)\n    import bisect\n    for value in values:\n        counts[bisect.bisect_left(limits, value)] += 1\n    return " ".join(map(str, counts))\n''',
"retry_schedule": '''def solve(data: str) -> str:\n    initial, factor, cap, attempts = map(int, data.split())\n    delay = initial\n    elapsed = 0\n    out = []\n    for _ in range(attempts):\n        elapsed += delay\n        out.append(str(elapsed))\n        delay = min(cap, delay * factor)\n    return " ".join(out)\n''',
"event_merge": '''def solve(data: str) -> str:\n    lines = data.strip().splitlines()\n    k = int(lines[0])\n    merged = []\n    for source in range(1, k + 1):\n        row = list(map(int, lines[source].split()))\n        for value in row[1:1+row[0]]:\n            merged.append((value, source))\n    merged.sort()\n    return " ".join(f"{value}:{source}" for value, source in merged)\n''',
"cache_expiry": '''def solve(data: str) -> str:\n    lines = data.strip().splitlines()\n    q = int(lines[0])\n    expires = {}\n    out = []\n    for line in lines[1:1+q]:\n        parts = line.split()\n        now = int(parts[0])\n        op = parts[1]\n        key = parts[2]\n        if op == "SET":\n            expires[key] = now + int(parts[3])\n        else:\n            out.append("HIT" if expires.get(key, -1) > now else "MISS")\n    return "\\n".join(out)\n''',
"shard_capacity": '''def solve(data: str) -> str:\n    nums = list(map(int, data.split()))\n    n, workers = nums[0], nums[1]\n    weights = nums[2:2+n]\n    lo, hi = max(weights), sum(weights)\n    def feasible(cap):\n        used = 1\n        load = 0\n        for w in weights:\n            if load + w > cap:\n                used += 1\n                load = w\n            else:\n                load += w\n        return used <= workers\n    while lo < hi:\n        mid = (lo + hi) // 2\n        if feasible(mid): hi = mid\n        else: lo = mid + 1\n    return str(lo)\n''',
"dependency_waves": '''def solve(data: str) -> str:\n    from collections import deque\n    nums = list(map(int, data.split()))\n    n, m = nums[0], nums[1]\n    g = [[] for _ in range(n)]\n    indeg = [0] * n\n    p = 2\n    for _ in range(m):\n        a, b = nums[p]-1, nums[p+1]-1; p += 2\n        g[a].append(b); indeg[b] += 1\n    q = deque(i for i, d in enumerate(indeg) if d == 0)\n    wave = [1] * n\n    seen = 0\n    while q:\n        u = q.popleft(); seen += 1\n        for v in g[u]:\n            wave[v] = max(wave[v], wave[u] + 1)\n            indeg[v] -= 1\n            if indeg[v] == 0: q.append(v)\n    if seen != n: return "CYCLE"\n    return " ".join(map(str, wave))\n''',
"quorum_window": '''def solve(data: str) -> str:\n    nums = list(map(int, data.split()))\n    n, services, quota = nums[0], nums[1], nums[2]\n    events = [(nums[3+2*i], nums[4+2*i]-1) for i in range(n)]\n    counts = [0] * services\n    satisfied = 0\n    left = 0\n    best = None\n    for right, (time, svc) in enumerate(events):\n        counts[svc] += 1\n        if counts[svc] == quota: satisfied += 1\n        while satisfied == services and left <= right:\n            best = min(best, time - events[left][0]) if best is not None else time - events[left][0]\n            old = events[left][1]\n            if counts[old] == quota: satisfied -= 1\n            counts[old] -= 1\n            left += 1\n    return str(best if best is not None else -1)\n''',
"nearest_pairs": '''def solve(data: str) -> str:\n    nums = list(map(int, data.split()))\n    pairs = nums[0]\n    indexed = sorted((value, i+1) for i, value in enumerate(nums[1:1+2*pairs]))\n    out = []\n    for i in range(0, len(indexed), 2):\n        out.append(f"{indexed[i][1]} {indexed[i+1][1]}")\n    return "\\n".join(out)\n''',
}

PAIR_CHECKER = r'''#!/usr/bin/env python3
from __future__ import annotations
import sys


def fail(message: str) -> None:
    print("0")
    print(message, file=sys.stderr)
    raise SystemExit(0)


def main() -> None:
    if len(sys.argv) != 4:
        fail("expected: checker.py input expected actual")
    values = list(map(int, open(sys.argv[1], encoding="utf-8").read().split()))
    pair_count = values[0]
    weights = values[1:1 + 2 * pair_count]
    tokens = open(sys.argv[3], encoding="utf-8").read().split()
    if len(tokens) != 2 * pair_count:
        fail("wrong number of indices")
    try:
        ids = list(map(int, tokens))
    except ValueError:
        fail("indices must be integers")
    if sorted(ids) != list(range(1, 2 * pair_count + 1)):
        fail("every index must appear exactly once")
    actual_cost = 0
    for i in range(0, len(ids), 2):
        actual_cost += abs(weights[ids[i]-1] - weights[ids[i+1]-1])
    ordered = sorted(weights)
    optimum = sum(abs(ordered[i] - ordered[i+1]) for i in range(0, len(ordered), 2))
    if actual_cost != optimum:
        fail(f"pairing cost {actual_cost}, optimum {optimum}")
    print("1")


if __name__ == "__main__":
    main()
'''

SPECS = [
    ChallengeBlueprint("signal-window", "SW01", "Peak Signal Window", "easy", 900, ("sliding-window", "arrays", "monitoring"),
        "A monitoring agent recorded a signed signal once per second. Find the largest total signal observed in any contiguous window of exactly k samples.",
        "The first line contains n and k. The second line contains n signed integers.",
        "Print one integer: the maximum sum over all contiguous windows of length k.", MODELS["signal_window"], signal_window_cases, ("5 3\n1 2 3 4 5\n", "6 2\n-5 -2 -7 -1 -3 -4\n")),
    ChallengeBlueprint("gap-monitor", "GM02", "Longest Quiet Gap", "easy", 900, ("simulation", "timestamps", "monitoring"),
        "Given non-decreasing event timestamps, locate the largest gap between consecutive events. When several gaps are equal, keep the earliest one.",
        "The first line contains n >= 2. The second line contains n non-decreasing integer timestamps.",
        "Print the gap length and the 1-based index of the event that ends that gap.", MODELS["gap_monitor"], gap_monitor_cases, ("5\n0 4 4 9 21\n",)),
    ChallengeBlueprint("batch-dedup", "BD03", "Stable Batch Deduplication", "easy", 1000, ("hash-set", "strings", "streaming"),
        "A batch may contain repeated keys. Keep only the first occurrence of each key while preserving the original order.",
        "The first line contains n. The second line contains n whitespace-free keys.",
        "Print the number of retained keys, then the retained keys on the next line.", MODELS["batch_dedup"], batch_dedup_cases, ("6\na b a c b d\n",)),
    ChallengeBlueprint("latency-buckets", "LB04", "Latency Histogram", "easy", 1000, ("binary-search", "histogram", "observability"),
        "Build a histogram of request latencies using sorted inclusive bucket limits. Values above the last limit belong to an overflow bucket.",
        "The first line contains b and n. The second line has b strictly increasing bucket limits. The third line has n non-negative latencies.",
        "Print b+1 counts: one count for each <= limit bucket followed by the overflow count.", MODELS["latency_buckets"], latency_bucket_cases, ("3 7\n50 100 250\n10 50 51 100 101 250 999\n",)),
    ChallengeBlueprint("retry-schedule", "RS05", "Capped Retry Schedule", "easy", 1000, ("simulation", "backoff", "reliability"),
        "A client retries after an exponentially growing delay. The delay is multiplied by a factor after every retry but never exceeds a cap.",
        "Four integers: initialDelay, factor, cap, attempts.",
        "Print the cumulative elapsed time at which each retry starts.", MODELS["retry_schedule"], retry_schedule_cases, ("5 2 20 5\n",)),
    ChallengeBlueprint("event-merge", "EM06", "Merge Event Streams", "medium", 1200, ("sorting", "streams", "merge"),
        "Merge several already sorted event streams. Each emitted item keeps the 1-based stream number; ties are ordered by stream number.",
        "The first line contains k. Each of the next k lines starts with m followed by m sorted integer event values.",
        "Print merged items as value:stream tokens separated by spaces.", MODELS["event_merge"], event_merge_cases, ("3\n3 1 4 8\n2 1 7\n4 2 2 9 10\n",)),
    ChallengeBlueprint("cache-expiry", "CE07", "TTL Cache Timeline", "medium", 1300, ("simulation", "hash-map", "ttl"),
        "Replay a timestamped cache log. SET replaces the expiration time. A GET is a hit only when the key exists and its expiration time is strictly greater than the GET timestamp.",
        "The first line contains q. Each following line is either 't SET key ttl' or 't GET key'. Timestamps are non-decreasing.",
        "For each GET operation print HIT or MISS on its own line.", MODELS["cache_expiry"], cache_expiry_cases, ("7\n0 SET a 5\n2 GET a\n5 GET a\n6 SET a 2\n7 GET a\n8 GET a\n9 GET b\n",)),
    ChallengeBlueprint("shard-capacity", "SC08", "Contiguous Shard Capacity", "medium", 1500, ("binary-search", "greedy", "partitioning"),
        "Split a fixed-order sequence of jobs across at most m workers. Each worker receives one contiguous block. Minimize the largest total weight assigned to any worker.",
        "The first line contains n and m. The second line contains n positive job weights.",
        "Print the minimum possible maximum worker load.", MODELS["shard_capacity"], shard_capacity_cases, ("5 2\n7 2 5 10 8\n",)),
    ChallengeBlueprint("dependency-waves", "DW09", "Deployment Waves", "medium", 1500, ("graphs", "topological-sort", "dag"),
        "Services may deploy only after all prerequisites have deployed. Assign every service the earliest possible deployment wave, starting from wave 1. Cyclic dependency graphs cannot be scheduled.",
        "The first line contains n and m. Each of the next m lines contains edge a b meaning a must deploy before b.",
        "Print CYCLE if the graph is cyclic. Otherwise print n earliest wave numbers in service order.", MODELS["dependency_waves"], dependency_wave_cases, ("5 4\n1 3\n2 3\n3 4\n3 5\n", "3 3\n1 2\n2 3\n3 1\n")),
    ChallengeBlueprint("quorum-window", "QW10", "Smallest Quorum Window", "hard", 1700, ("two-pointers", "events", "sliding-window"),
        "An incident is considered observable only when every service has emitted at least q events inside the same time interval. Find the narrowest interval represented by a contiguous slice of the event log.",
        "The first line contains n, s and q. The next n lines contain timestamp and serviceId. Timestamps are non-decreasing and service ids are from 1 to s.",
        "Print the minimum timestamp width of a qualifying window, or -1 if no such window exists.", MODELS["quorum_window"], quorum_window_cases, ("8 3 2\n1 1\n2 2\n3 3\n4 1\n6 2\n7 3\n9 1\n12 2\n",)),
    ChallengeBlueprint("nearest-pairs", "NP11", "Optimal Neighbour Pairing", "hard", 1800, ("greedy", "sorting", "custom-checker"),
        "Pair all 2n items so that the sum of absolute differences inside pairs is as small as possible. Any optimal pairing is accepted.",
        "The first line contains n. The second line contains 2n distinct integer weights.",
        "Print n lines. Each line contains two 1-based item indices. Every index must appear exactly once, and the pairing must have minimum total cost.", MODELS["nearest_pairs"], nearest_pair_cases, ("3\n10 1 8 3 4 20\n",), checker_kind="custom", checker_source=PAIR_CHECKER),
]


def materialize_challenge(spec: ChallengeBlueprint) -> dict[str, object]:
    challenge_key = f"rl-{spec.slug}"
    bundle = CHALLENGES_ROOT / challenge_key
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "model").mkdir(exist_ok=True)
    (bundle / "samples").mkdir(exist_ok=True)
    (bundle / "tests").mkdir(exist_ok=True)
    if spec.checker_source:
        (bundle / "checker").mkdir(exist_ok=True)
        (bundle / "checker" / "checker.py").write_text(spec.checker_source, encoding="utf-8")

    model_file = bundle / "model" / "sol.py"
    model_file.write_text(spec.reference_source + "\n\nif __name__ == '__main__':\n    import sys\n    print(solve(sys.stdin.read()))\n", encoding="utf-8")

    sample_records = []
    for index, sample_input in enumerate(spec.examples, 1):
        sample_output = solve_with_model(spec.reference_source, sample_input)
        (bundle / "samples" / f"{index:02d}.in").write_text(sample_input, encoding="utf-8")
        (bundle / "samples" / f"{index:02d}.out").write_text(sample_output, encoding="utf-8")
        sample_records.append({"stdin": sample_input.rstrip("\n"), "stdout": sample_output.rstrip("\n"), "explanation": None})

    test_cases = spec.case_factory()
    for index, test_input in enumerate(test_cases, 1):
        expected = solve_with_model(spec.reference_source, test_input)
        (bundle / "tests" / f"{index:02d}.in").write_text(test_input, encoding="utf-8")
        (bundle / "tests" / f"{index:02d}.out").write_text(expected, encoding="utf-8")

    checker: dict[str, object] = {"kind": spec.checker_kind, "script": None, "options": {}}
    if spec.checker_source:
        checker["script"] = "checker/checker.py"
    metadata = {
        "key": challenge_key,
        "shortCode": spec.short_code,
        "name": spec.name,
        "origin": {"platform": "runline-labs", "license": "CC0-1.0", "category": "portfolio-demo"},
        "level": spec.level,
        "score": spec.score,
        "labels": list(spec.labels),
        "mode": "stdio",
        "runtimes": ["Python", "C++", "Java", "Rust", "Go"],
        "budget": {"cpuMillis": spec.cpu_millis, "memoryMiB": spec.memory_mib, "derived": False},
        "input": {"mode": "stdio", "inputFile": None, "outputFile": None},
        "prompt": {"overview": spec.overview, "inputContract": spec.input_contract, "outputContract": spec.output_contract, "interactionContract": None, "notes": spec.notes},
        "examples": sample_records,
        "evaluation": {"checker": checker, "interactor": None},
        "references": [{"runtime": "Python", "entry": "model/sol.py"}],
        "suite": {"directory": "tests", "cases": len(test_cases), "visible": len(spec.examples), "complete": True},
        "artifact": {"kind": "source", "extensions": [".py", ".cpp", ".cc", ".c", ".java", ".rs", ".go"], "entrypoint": None},
        "acceptedCount": 0,
        "enabled": True,
    }
    (bundle / "challenge.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    notes = f"\n\n## Notes\n\n{spec.notes}" if spec.notes else ""
    markdown = dedent(f"""\
    # {spec.name}

    {spec.overview}

    ## Input

    {spec.input_contract}

    ## Output

    {spec.output_contract}{notes}
    """)
    (bundle / "statement.md").write_text(markdown, encoding="utf-8")
    return {
        "key": challenge_key,
        "shortCode": spec.short_code,
        "name": spec.name,
        "level": spec.level,
        "score": spec.score,
        "labels": list(spec.labels),
        "mode": "stdio",
        "runtimes": ["Python", "C++", "Java", "Rust", "Go"],
        "budget": {"cpuMillis": spec.cpu_millis, "memoryMiB": spec.memory_mib, "derived": False},
        "acceptedCount": 0,
        "customChecker": spec.checker_kind != "token",
        "interactive": False,
        "origin": {"platform": "runline-labs", "license": "CC0-1.0", "category": "portfolio-demo"},
    }


def main() -> None:
    if CHALLENGES_ROOT.exists():
        for child in CHALLENGES_ROOT.iterdir():
            if child.name != ".gitkeep":
                shutil.rmtree(child) if child.is_dir() else child.unlink()
    else:
        CHALLENGES_ROOT.mkdir(parents=True)
    index = [materialize_challenge(spec) for spec in SPECS]
    (CHALLENGES_ROOT / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"rebuilt {len(index)} Runline Labs challenge bundles")


if __name__ == "__main__":
    main()
