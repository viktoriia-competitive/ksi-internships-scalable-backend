# Decision 001 — inward-facing ports

Status: accepted.

Use cases receive structural interfaces for catalogues, attempts, accounts,
lifecycle facts, revisions, transactions, and the command outbox. HTTP models and
ORM rows terminate at their adapters. Immutable domain records cross the inner
boundary.

This allows API fields and SQL layout to change independently, and keeps most
workflow tests free of FastAPI and PostgreSQL. Explicit mapping is accepted as
the cost of preventing framework types from becoming the business model.
