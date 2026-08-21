def solve(data: str) -> str:
    parts = data.split()
    n = int(parts[0])
    seen = set()
    out = []
    for token in parts[1:1+n]:
        if token not in seen:
            seen.add(token)
            out.append(token)
    return str(len(out)) + "\n" + " ".join(out)


if __name__ == '__main__':
    import sys
    print(solve(sys.stdin.read()))
