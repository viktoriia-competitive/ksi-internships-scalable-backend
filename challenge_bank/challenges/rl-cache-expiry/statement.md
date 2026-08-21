# TTL Cache Timeline

Replay a timestamped cache log. SET replaces the expiration time. A GET is a hit only when the key exists and its expiration time is strictly greater than the GET timestamp.

## Input

The first line contains q. Each following line is either 't SET key ttl' or 't GET key'. Timestamps are non-decreasing.

## Output

For each GET operation print HIT or MISS on its own line.
