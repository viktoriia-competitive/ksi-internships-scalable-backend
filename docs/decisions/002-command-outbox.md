# Decision 002 — stage evaluation commands transactionally

Status: accepted.

Opening an attempt and staging its `EvaluationCommand` happen in one PostgreSQL
transaction. A dispatcher later copies the encoded command from `control_outbox`
to the appropriate Redis work stream.

Redis availability therefore does not decide whether an accepted API write is
recoverable. Delivery remains at least once. `delivery_key`, lifecycle dedupe
keys, and `processed_commands` make duplicate persistence harmless. Operations
must observe pending outbox records and the dead-work stream.
