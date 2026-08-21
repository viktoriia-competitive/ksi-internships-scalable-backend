def solve(data: str) -> str:
    nums = list(map(int, data.split()))
    n, workers = nums[0], nums[1]
    weights = nums[2:2+n]
    lo, hi = max(weights), sum(weights)
    def feasible(cap):
        used = 1
        load = 0
        for w in weights:
            if load + w > cap:
                used += 1
                load = w
            else:
                load += w
        return used <= workers
    while lo < hi:
        mid = (lo + hi) // 2
        if feasible(mid): hi = mid
        else: lo = mid + 1
    return str(lo)


if __name__ == '__main__':
    import sys
    print(solve(sys.stdin.read()))
