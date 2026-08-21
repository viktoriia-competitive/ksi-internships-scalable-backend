def solve(data: str) -> str:
    values = list(map(int, data.split()))
    n = values[0]
    ts = values[1:1+n]
    best_gap = -1
    best_end = 2
    for i in range(1, n):
        gap = ts[i] - ts[i-1]
        if gap > best_gap:
            best_gap, best_end = gap, i + 1
    return f"{best_gap} {best_end}"


if __name__ == '__main__':
    import sys
    print(solve(sys.stdin.read()))
