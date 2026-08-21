# Capped Retry Schedule

A client retries after an exponentially growing delay. The delay is multiplied by a factor after every retry but never exceeds a cap.

## Input

Four integers: initialDelay, factor, cap, attempts.

## Output

Print the cumulative elapsed time at which each retry starts.
