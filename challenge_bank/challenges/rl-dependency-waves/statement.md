# Deployment Waves

Services may deploy only after all prerequisites have deployed. Assign every service the earliest possible deployment wave, starting from wave 1. Cyclic dependency graphs cannot be scheduled.

## Input

The first line contains n and m. Each of the next m lines contains edge a b meaning a must deploy before b.

## Output

Print CYCLE if the graph is cyclic. Otherwise print n earliest wave numbers in service order.
