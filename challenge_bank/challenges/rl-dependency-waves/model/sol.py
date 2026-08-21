def solve(data: str) -> str:
    from collections import deque
    nums = list(map(int, data.split()))
    n, m = nums[0], nums[1]
    g = [[] for _ in range(n)]
    indeg = [0] * n
    p = 2
    for _ in range(m):
        a, b = nums[p]-1, nums[p+1]-1; p += 2
        g[a].append(b); indeg[b] += 1
    q = deque(i for i, d in enumerate(indeg) if d == 0)
    wave = [1] * n
    seen = 0
    while q:
        u = q.popleft(); seen += 1
        for v in g[u]:
            wave[v] = max(wave[v], wave[u] + 1)
            indeg[v] -= 1
            if indeg[v] == 0: q.append(v)
    if seen != n: return "CYCLE"
    return " ".join(map(str, wave))


if __name__ == '__main__':
    import sys
    print(solve(sys.stdin.read()))
