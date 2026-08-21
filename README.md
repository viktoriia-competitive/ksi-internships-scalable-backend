<div align="center">

# Runline

### Reliable asynchronous online judge control plane & evaluation platform

**Runline** is a full-stack programming judge built around durable command delivery, isolated code execution, explicit lifecycle events, and recoverable asynchronous processing.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](#technology-stack)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](#technology-stack)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)](#technology-stack)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](#technology-stack)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](#technology-stack)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](#technology-stack)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](#quick-start)

</div>

---

## Contents

- [Why Runline](#why-runline)
- [System Architecture](#system-architecture)
- [Submission Flow](#submission-flow)
- [Attempt Lifecycle](#attempt-lifecycle)
- [Reliability Model](#reliability-model)
- [Execution Engine](#execution-engine)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Development Commands](#development-commands)
- [Challenge Bank](#challenge-bank)
- [API](#api)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Testing](#testing)
- [Security & Isolation](#security--isolation)
- [Architecture Decisions](#architecture-decisions)
- [Current Scope](#current-scope)

---

## Why Runline

A naive online judge can execute user code directly inside an HTTP request. That works for a prototype, but it couples API latency, execution failures, persistence, and process isolation into a single failure domain.

Runline takes a different approach: **the API records intent, PostgreSQL owns durable facts, Redis delivers work, and workers execute submissions asynchronously**.

| Design goal | Runline approach |
|---|---|
| Keep HTTP requests fast | Submission requests create durable work and return `202 Accepted` |
| Avoid losing accepted submissions | Evaluation commands are staged with a transactional outbox |
| Survive worker crashes | Redis Streams consumer groups support pending-message reclamation |
| Make redelivery safe | Delivery keys + `processed_commands` provide an idempotency boundary |
| Preserve execution history | Lifecycle events are persisted as ordered facts |
| Isolate platform-specific execution | Process mechanics live behind `SandboxProvider` |
| Keep challenge evaluation reproducible | Commands can reference immutable challenge revisions |
| Make failures diagnosable | Attempt reports include per-test verdicts and resource observations |

### Core capabilities

- asynchronous submission evaluation;
- transactional outbox delivery;
- Redis Streams worker queue;
- retry and dead-letter handling;
- idempotent terminal-result persistence;
- lifecycle timeline and disposable attempt projections;
- immutable challenge revisions;
- Monaco-based browser editor;
- deterministic challenge/test catalogue;
- compilation, execution, output checking, and resource-aware verdicts;
- Docker Compose development environment;
- health/readiness checks and development diagnostics.

---

## System Architecture

```mermaid
flowchart TB
    subgraph Client[Client Layer]
        Browser[Browser]
        Console[Next.js 15 Console\nReact 19 + Monaco]
        Browser --> Console
    end

    subgraph Control[Control Plane]
        API[FastAPI API\n/control/v2]
        UC[Application Use Cases]
        Ports[Inward-facing Ports]
        API --> UC --> Ports
    end

    subgraph State[Durable State]
        PG[(PostgreSQL 16)]
        Outbox[(control_outbox)]
        Events[(Lifecycle Events)]
        Attempts[(Attempts / Projections)]
        Processed[(processed_commands)]
        PG --- Outbox
        PG --- Events
        PG --- Attempts
        PG --- Processed
    end

    subgraph Messaging[Async Delivery]
        Streams[(Redis 7 Streams)]
        Dead[(Dead-work Stream)]
    end

    subgraph WorkerLayer[Evaluation Worker]
        Dispatcher[Outbox Dispatcher]
        Consumer[Consumer Group Worker]
        Evaluator[Evaluation Coordinator]
        Dispatcher --> Consumer --> Evaluator
    end

    subgraph Execution[Execution Boundary]
        Runner[Runtime Preparer]
        Sandbox[SandboxProvider]
        Checker[Output Checker]
        Policy[Verdict Policy]
        Runner --> Sandbox
        Sandbox --> Policy
        Sandbox --> Checker
    end

    subgraph Content[Challenge Content]
        Bank[Challenge Bank]
        Revision[Immutable Revision]
        Tests[Test Cases]
        Bank --> Revision --> Tests
    end

    Console -->|HTTP| API
    Ports -->|transaction| PG
    Outbox --> Dispatcher
    Dispatcher -->|XADD| Streams
    Streams -->|consumer group| Consumer
    Consumer -->|retry exhausted| Dead
    Evaluator --> Runner
    Evaluator --> Revision
    Checker --> Tests
    Evaluator -->|verdict + report + events| PG
    API -->|read models| PG
    Console -->|poll/read attempt| API
```

### Deployment topology

```mermaid
flowchart LR
    User[Developer / User]

    subgraph Docker[Docker Compose: runline]
        Console[console\n:3000]
        API[api\n:8000]
        Worker[worker]
        Seed[seed]
        PG[(postgres\n:5432)]
        Redis[(redis\n:6379)]

        Console -->|API_URL=http://api:8000| API
        API --> PG
        API --> Redis
        Worker --> PG
        Worker --> Redis
        Seed --> PG
    end

    User -->|http://localhost:3000| Console
    User -->|http://localhost:8000| API
```

The browser uses `NEXT_PUBLIC_API_URL=http://localhost:8000`, while Next.js server-side code uses Docker DNS through `API_URL=http://api:8000`.

---

## Submission Flow

The submission path is deliberately split between **durable acceptance** and **asynchronous execution**.

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant UI as Next.js Console
    participant API as FastAPI
    participant DB as PostgreSQL
    participant D as Outbox Dispatcher
    participant R as Redis Streams
    participant W as Evaluation Worker
    participant E as Execution Engine

    U->>UI: Submit source code
    UI->>API: POST /control/v2/attempts

    rect rgb(245,245,245)
        Note over API,DB: Single database transaction
        API->>DB: Insert attempt
        API->>DB: Append lifecycle facts
        API->>DB: Insert EvaluationCommand into outbox
    end

    API-->>UI: 202 Accepted + attempt key

    loop Outbox dispatch
        D->>DB: Read unpublished commands
        D->>R: XADD evaluation command
        D->>DB: Mark outbox row published
    end

    W->>R: Claim command via consumer group
    W->>DB: Claim attempt + append execution.claimed
    W->>E: Evaluate immutable challenge revision
    E-->>W: SuiteResult + per-test metrics

    alt Evaluation completed
        W->>DB: Persist verdict + report + processed key
        W->>R: ACK command
    else Transient infrastructure failure
        W->>DB: Record retryable failure
        W->>R: Requeue retry command
    else Retry budget exhausted
        W->>DB: Persist INTERNAL_ERROR
        W->>R: Move to dead-work stream
    end

    UI->>API: GET attempt / timeline
    API->>DB: Read current projection + facts
    API-->>UI: Verdict and report
```

### Why the outbox exists

The API does **not** need Redis to be available at the exact instant a submission is accepted. The attempt and its `EvaluationCommand` are committed together in PostgreSQL. If Redis is temporarily unavailable, the pending outbox record remains recoverable and can be published later.

---

## Attempt Lifecycle

Runline keeps an ordered lifecycle event stream and derives the current attempt projection from those facts.

```mermaid
stateDiagram-v2
    [*] --> QUEUED: attempt.opened / execution.requested
    QUEUED --> RUNNING: execution.claimed
    RUNNING --> QUEUED: execution.retryable_failure

    RUNNING --> ACCEPTED: execution.completed
    RUNNING --> WRONG_ANSWER: execution.completed
    RUNNING --> TIME_LIMIT: execution.completed
    RUNNING --> MEMORY_LIMIT: execution.completed
    RUNNING --> RUNTIME_ERROR: execution.completed
    RUNNING --> COMPILATION_ERROR: execution.completed
    RUNNING --> INTERNAL_ERROR: execution.completed
    RUNNING --> INTERNAL_ERROR: execution.terminal_failure

    ACCEPTED --> [*]
    WRONG_ANSWER --> [*]
    TIME_LIMIT --> [*]
    MEMORY_LIMIT --> [*]
    RUNTIME_ERROR --> [*]
    COMPILATION_ERROR --> [*]
    INTERNAL_ERROR --> [*]
```

Terminal states are:

`ACCEPTED` · `WRONG_ANSWER` · `TIME_LIMIT` · `MEMORY_LIMIT` · `RUNTIME_ERROR` · `COMPILATION_ERROR` · `INTERNAL_ERROR`

The projection is intentionally disposable: it can be rebuilt by replaying lifecycle events in sequence order.

---

## Reliability Model

Runline follows a simple ownership rule:

> **PostgreSQL owns facts. Redis owns delivery.**

```mermaid
flowchart LR
    A[HTTP submission] --> T{PostgreSQL transaction}
    T -->|commit| Attempt[Attempt + lifecycle]
    T -->|commit| Outbox[Evaluation command]

    Outbox --> Dispatch[Dispatcher]
    Dispatch --> Redis[(Redis Stream)]
    Redis --> Worker[Worker]

    Worker --> Check{delivery_key\nalready processed?}
    Check -->|yes| Ack[ACK duplicate]
    Check -->|no| Run[Execute]

    Run --> Success{Execution path}
    Success -->|judge result| Persist[Persist result + processed key\nin one DB transaction]
    Success -->|transient failure| Retry[Create retry command]
    Success -->|attempts exhausted| Terminal[Persist INTERNAL_ERROR]

    Persist --> Ack
    Retry --> Redis
    Terminal --> Dead[(Dead-work stream)]
```

### Failure semantics

| Failure | Expected behavior |
|---|---|
| API crashes before DB commit | No accepted attempt exists |
| API commits, Redis is unavailable | Outbox retains recoverable work |
| Dispatcher publishes twice | Duplicate delivery is tolerated |
| Worker crashes after claiming | Pending Redis message can be reclaimed |
| Worker crashes after DB commit but before ACK | `processed_commands` makes redelivery harmless |
| Evaluation infrastructure fails transiently | Attempt returns to `QUEUED` with incremented retry index |
| Retry budget is exhausted | Attempt becomes `INTERNAL_ERROR`; work enters dead stream |

### Idempotency boundaries

Runline uses multiple keys for different forms of duplicate protection:

- request keys — duplicate attempt creation protection;
- `delivery_key` — command-delivery identity;
- lifecycle `dedupe_key` — duplicate event protection;
- `processed_commands` — terminal worker-side idempotency boundary;
- deterministic `run_key` / retry keys — stable execution identity.

---

## Execution Engine

The judge engine is separated from queueing and persistence. It receives a source artifact plus a challenge bundle and returns a structured suite result.

```mermaid
flowchart LR
    Source[Source Artifact]
    Bundle[Challenge Bundle]

    Source --> Prepare[Runtime preparation / compilation]
    Bundle --> Limits[Per-test limits]
    Bundle --> Cases[Test cases]
    Bundle --> CheckerSpec[Checker specification]

    Prepare -->|compile failure| CE[COMPILATION_ERROR]
    Prepare --> Exec[ProgramRunner]
    Limits --> Exec
    Cases --> Exec

    Exec --> Sandbox[SandboxProvider]
    Sandbox --> Obs[SandboxResult\nexit · signal · CPU · wall · memory]

    Obs --> Policy[VerdictPolicy]
    Policy -->|timeout| TLE[TIME_LIMIT]
    Policy -->|OOM / memory| MLE[MEMORY_LIMIT]
    Policy -->|bad exit| RE[RUNTIME_ERROR]
    Policy -->|process OK| Compare[Output Checker]

    CheckerSpec --> Compare
    Cases --> Compare

    Compare -->|match| OK[Test Accepted]
    Compare -->|mismatch| WA[WRONG_ANSWER]

    OK --> Suite[Suite Aggregation]
    WA --> Suite
    TLE --> Suite
    MLE --> Suite
    RE --> Suite
    CE --> Suite

    Suite --> Result[SuiteResult\nverdict + counts + max resources + per-test report]
```

### Verdict policy

For every test case, the engine converts low-level process observations into contestant-facing verdicts. It evaluates OOM kills, wall-clock termination, enforced CPU/memory limits, process exit status, and finally output correctness.

### Output checking

The engine supports:

- whitespace-token comparison for standard deterministic tasks;
- Python custom checker execution for challenge-specific judging logic.

### Runtime support

| Runtime | Catalogue / contracts | Local preparer |
|---|:---:|:---:|
| Python | ✅ | ✅ |
| C++ | ✅ | ✅ |
| Java | ✅ | 🚧 |
| Rust | ✅ | 🚧 |
| Go | ✅ | 🚧 |
| Bash | internal engine path | ✅ |

Java, Rust, and Go are represented by the current runtime contracts/toolchain diagnostics, but the checked-in preparer map currently implements Python, C++, and Bash. The shipped challenge catalogue should therefore be treated according to the executable preparers available in the environment.

---

## Technology Stack

| Layer | Technology | Responsibility |
|---|---|---|
| Web console | Next.js 15, React 19, TypeScript 5.7, Tailwind CSS | Challenge catalogue, editor, submissions, history |
| Editor | Monaco Editor | Browser-based source editing |
| HTTP API | FastAPI, Pydantic v2 | Versioned contracts, validation, routing |
| Application layer | Python use cases + structural ports | Framework-independent workflows |
| Persistence | PostgreSQL 16, SQLAlchemy Async, asyncpg | Attempts, accounts, events, outbox, projections |
| Messaging | Redis 7 Streams | Durable worker delivery, consumer groups, retries |
| Worker | Python / asyncio | Dispatch, consumption, evaluation, persistence |
| Judge engine | Python | Compile/run/check orchestration and verdict policy |
| Isolation | Linux process provider + optional cgroup v2 | Deadlines and resource observations |
| Development | Docker Compose | Local multi-service orchestration |

---

## Quick Start

### Prerequisites

Install:

- Docker Desktop or Docker Engine;
- Docker Compose v2;
- `curl` for host-side readiness diagnostics.

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd runline-control-plane-redesign
```

### 2. Start the stack

```bash
chmod +x dev.sh
./dev.sh
```

The launcher builds and starts PostgreSQL, Redis, the challenge seed job, FastAPI API, evaluation worker, and Next.js console.

### 3. Open Runline

| Service | Address |
|---|---|
| Web console | `http://localhost:3000` |
| API | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| Liveness | `http://localhost:8000/live` |
| Readiness | `http://localhost:8000/ready` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |

---

## Development Commands

```bash
./dev.sh                 # build and start the full stack
./dev.sh down            # stop containers, preserve volumes
./dev.sh restart         # restart all services
./dev.sh rebuild         # rebuild images without cache
./dev.sh reset           # remove local volumes and recreate the stack
./dev.sh status          # show service status
./dev.sh logs            # follow all logs
./dev.sh logs api        # follow API logs
./dev.sh logs worker     # follow worker logs
./dev.sh doctor          # validate Compose and inspect service health
```

A typical troubleshooting cycle is:

```bash
./dev.sh doctor
./dev.sh logs api
./dev.sh logs worker
```

---

## Challenge Bank

The repository includes a generated portfolio challenge catalogue with:

- **11 challenge bundles**;
- **220 deterministic test cases**;
- multiple difficulty levels;
- statements and public samples;
- hidden evaluation cases;
- reference implementations;
- per-case time and memory budgets;
- optional custom checker support.

A challenge bundle follows this general layout:

```text
challenge_bank/challenges/<challenge-key>/
├── challenge.json       # metadata, runtimes, limits, checker policy
├── statement.md         # problem statement
├── samples/             # public sample I/O
├── tests/               # evaluation cases
├── model/               # reference implementation
└── checker/             # optional custom checker
```

Audit the complete catalogue with:

```bash
python tooling/audit_challenge_bank.py
```

Current audited result:

```text
audited 11 challenge bundles and 220 cases
```

### Immutable revisions

Queued commands can carry a `challenge_digest`. When present, the worker evaluates the materialized immutable revision rather than mutable working-tree challenge content. This prevents a queued submission from silently changing meaning after challenge files are edited.

---

## API

The public API is versioned under:

```text
/control/v2
```

### Challenges

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/control/v2/challenges` | Browse/filter/sort/paginate challenges |
| `GET` | `/control/v2/challenges/{challengeKey}` | Read a challenge |
| `GET` | `/control/v2/challenges/{challengeKey}/attempts` | Read attempts for a challenge |

### Attempts

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/control/v2/attempts` | Open and queue a new attempt |
| `GET` | `/control/v2/attempts` | Browse attempts |
| `GET` | `/control/v2/attempts/{attemptKey}` | Read attempt state/report |
| `GET` | `/control/v2/attempts/{attemptKey}/source` | Download submitted source |
| `GET` | `/control/v2/attempts/{attemptKey}/timeline` | Read lifecycle events |

### Accounts

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/control/v2/accounts/self` | Current development account projection |
| `GET` | `/control/v2/accounts/by-handle/{handle}` | Resolve an account by handle |

### Example submission

```bash
curl -X POST http://localhost:8000/control/v2/attempts \
  -H 'Content-Type: application/json' \
  -H 'Request-Key: demo-request-001' \
  -d '{
    "challengeKey": "rl-batch-dedup",
    "runtime": "Python",
    "artifactName": "solution.py",
    "sourceText": "print(input())\n"
  }'
```

The API responds with HTTP `202 Accepted`; execution continues asynchronously.

---

## Project Structure

```text
runline-control-plane-redesign/
├── challenge_bank/
│   └── challenges/              # versioned challenge packages and tests
│
├── control_plane/
│   ├── runtime/
│   │   ├── adapters/            # Redis queue / notifications
│   │   ├── contracts/           # HTTP schemas
│   │   ├── core/                # domain records, status, lifecycle
│   │   ├── http/                # FastAPI routes and presenters
│   │   ├── persistence/         # repositories
│   │   ├── storage/             # SQLAlchemy/session/artifact infrastructure
│   │   ├── use_cases/           # application workflows and ports
│   │   └── worker/              # outbox dispatcher + evaluator consumer
│   ├── scripts/                 # seed / maintenance commands
│   └── tests/
│
├── execution_engine/
│   ├── core/                    # evaluation orchestration and policy
│   ├── outer/                   # toolchain / checker adapters
│   ├── platform/linux/          # Linux execution implementation
│   ├── contracts/               # protocol contracts
│   ├── fixtures/                # executable fixtures
│   ├── tools/                   # CLI diagnostics
│   ├── docs/                    # engine-specific notes
│   └── tests/
│
├── web_console/
│   ├── app/                     # Next.js App Router
│   ├── components/              # shared UI
│   ├── features/                # challenge / attempt / dashboard features
│   └── lib/                     # API client and contracts
│
├── docs/
│   └── decisions/               # architecture decision records
│
├── tooling/                     # challenge-bank generation and audit tools
├── docker-compose.yml
├── requirements-dev.txt
└── dev.sh                       # root development launcher
```

### Layer boundaries

```mermaid
flowchart LR
    HTTP[HTTP / FastAPI]
    UseCases[Use Cases]
    Core[Domain Records]
    Ports[Structural Ports]
    Adapters[Adapters]
    Infra[PostgreSQL / Redis / Filesystem]

    HTTP --> UseCases
    UseCases --> Core
    UseCases --> Ports
    Adapters -. implement .-> Ports
    Adapters --> Infra

    style Core stroke-width:3px
    style UseCases stroke-width:3px
```

HTTP models and ORM rows terminate at their adapters. Inner workflows operate on explicit domain records and ports rather than framework-specific types.

---

## Configuration

Backend configuration is provided through environment variables via Pydantic settings.

| Variable | Development default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://runline:runline@.../runline` | PostgreSQL connection |
| `REDIS_URL` | `redis://...:6379/0` | Redis connection |
| `API_PREFIX` | `/control/v2` | API version prefix |
| `CORS_ORIGINS` | local console origins | Browser API policy |
| `QUEUE_NAMESPACE` | `runline-control` | Redis namespace |
| `QUEUE_GROUP` | `evaluation-workers` | Consumer group |
| `QUEUE_MAX_ATTEMPTS` | `3` | Retry budget |
| `QUEUE_VISIBILITY_TIMEOUT_MS` | `60000` | Stale-message reclaim timeout |
| `AUTO_CREATE_SCHEMA` | `true` | Development schema creation |
| `EXECUTION_USE_CGROUP` | `false` | Optional cgroup-backed enforcement |
| `EXECUTION_ISOLATION` | `none` | Isolation configuration marker |

Frontend networking uses:

```text
API_URL=http://api:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

This distinction is intentional: Server Components execute inside the console container, while client-side browser code runs on the host.

---

## Testing

### Control plane

```bash
python -m pytest -q control_plane/tests
```

### Execution engine

```bash
python -m pytest -q execution_engine/tests
```

Some resource/isolation tests depend on Linux and cgroup capabilities.

### Engine smoke test

```bash
python -m execution_engine.tools.cli smoke
```

### Challenge catalogue audit

```bash
python tooling/audit_challenge_bank.py
```

### Frontend

```bash
cd web_console
npm install
npm run typecheck
npm run build
```

---

## Security & Isolation

The repository defines a `SandboxProvider` boundary so execution isolation can be replaced without rewriting challenge loading, worker delivery, persistence, or the public API.

The checked-in Linux provider supports development-oriented capabilities including:

- process-group execution;
- wall-clock deadlines;
- CPU and memory observation;
- optional cgroup v2 integration;
- timeout and OOM classification.

> [!WARNING]
> The included local process sandbox is **not a production-grade hostile-code security boundary**. Docker Compose currently sets `EXECUTION_USE_CGROUP=false`. Production use should replace or harden the provider with namespace/container/micro-VM isolation, filesystem restrictions, network denial, process-count limits, enforced CPU/memory quotas, syscall policy, and stronger artifact isolation.

The key architectural point is that this stronger provider can be introduced behind the existing `SandboxProvider` contract.

---

## Architecture Decisions

The repository documents important decisions under `docs/decisions/`.

### ADR 001 — Inward-facing ports

Use cases depend on structural interfaces for attempts, challenges, accounts, lifecycle facts, revisions, transactions, and the command outbox. FastAPI schemas and SQLAlchemy rows remain at the edges.

**Why:** framework/API/storage changes should not redefine the business model.

### ADR 002 — Transactional evaluation outbox

Attempt creation and `EvaluationCommand` staging occur in the same PostgreSQL transaction. A dispatcher later publishes the command to Redis.

**Why:** Redis availability should not determine whether an already accepted submission is recoverable.

### ADR 003 — Replaceable isolation provider

Process launch, cgroups, deadlines, filesystem exposure, and wait-status accounting are hidden behind `SandboxProvider`.

**Why:** a stronger production sandbox can replace the local Linux implementation without changing judge semantics or control-plane persistence.

---

## Current Scope

Runline intentionally exposes the boundary between **production-oriented architecture** and **development implementation**.

Current limitations include:

- the included process sandbox is intended for local development/capability testing rather than hostile multi-tenant code;
- cgroup enforcement is disabled by default in Docker Compose;
- Java, Rust, and Go toolchains may be detectable, but runtime preparation is not yet wired into the current preparer map;
- development identity is intentionally minimal and is not a complete authentication/authorization system;
- production operations should add metrics/alerts for outbox backlog, consumer lag, stale pending messages, retry rate, and dead-work accumulation.

These limitations are explicit rather than hidden behind production claims.

---

<div align="center">

### Runline

**Durable acceptance · asynchronous execution · observable lifecycle · replaceable isolation**

</div>
