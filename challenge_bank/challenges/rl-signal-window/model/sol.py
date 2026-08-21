def solve(data: str) -> str:
    it = iter(map(int, data.split()))
    n, k = next(it), next(it)
    values = [next(it) for _ in range(n)]
    current = sum(values[:k])
    best = current
    for i in range(k, n):
        current += values[i] - values[i-k]
        best = max(best, current)
    return str(best)


if __name__ == '__main__':
    import sys
    print(solve(sys.stdin.read()))
