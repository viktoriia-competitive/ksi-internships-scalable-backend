def solve(data: str) -> str:
    lines = data.strip().splitlines()
    k = int(lines[0])
    merged = []
    for source in range(1, k + 1):
        row = list(map(int, lines[source].split()))
        for value in row[1:1+row[0]]:
            merged.append((value, source))
    merged.sort()
    return " ".join(f"{value}:{source}" for value, source in merged)


if __name__ == '__main__':
    import sys
    print(solve(sys.stdin.read()))
