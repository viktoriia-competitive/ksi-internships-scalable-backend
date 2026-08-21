def solve(data: str) -> str:
    nums = list(map(int, data.split()))
    n, services, quota = nums[0], nums[1], nums[2]
    events = [(nums[3+2*i], nums[4+2*i]-1) for i in range(n)]
    counts = [0] * services
    satisfied = 0
    left = 0
    best = None
    for right, (time, svc) in enumerate(events):
        counts[svc] += 1
        if counts[svc] == quota: satisfied += 1
        while satisfied == services and left <= right:
            best = min(best, time - events[left][0]) if best is not None else time - events[left][0]
            old = events[left][1]
            if counts[old] == quota: satisfied -= 1
            counts[old] -= 1
            left += 1
    return str(best if best is not None else -1)


if __name__ == '__main__':
    import sys
    print(solve(sys.stdin.read()))
