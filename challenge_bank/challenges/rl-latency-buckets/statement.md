# Latency Histogram

Build a histogram of request latencies using sorted inclusive bucket limits. Values above the last limit belong to an overflow bucket.

## Input

The first line contains b and n. The second line has b strictly increasing bucket limits. The third line has n non-negative latencies.

## Output

Print b+1 counts: one count for each <= limit bucket followed by the overflow count.
