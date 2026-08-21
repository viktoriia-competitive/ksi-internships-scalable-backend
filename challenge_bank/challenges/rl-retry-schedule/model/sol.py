def solve(data: str) -> str:
    initial, factor, cap, attempts = map(int, data.split())
    delay = initial
    elapsed = 0
    out = []
    for _ in range(attempts):
        elapsed += delay
        out.append(str(elapsed))
        delay = min(cap, delay * factor)
    return " ".join(out)


if __name__ == '__main__':
    import sys
    print(solve(sys.stdin.read()))
