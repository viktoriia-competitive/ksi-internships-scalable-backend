# Smallest Quorum Window

An incident is considered observable only when every service has emitted at least q events inside the same time interval. Find the narrowest interval represented by a contiguous slice of the event log.

## Input

The first line contains n, s and q. The next n lines contain timestamp and serviceId. Timestamps are non-decreasing and service ids are from 1 to s.

## Output

Print the minimum timestamp width of a qualifying window, or -1 if no such window exists.
