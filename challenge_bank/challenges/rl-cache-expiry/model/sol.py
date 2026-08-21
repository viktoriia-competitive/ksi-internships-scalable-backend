def solve(data: str) -> str:
    lines = data.strip().splitlines()
    q = int(lines[0])
    expires = {}
    out = []
    for line in lines[1:1+q]:
        parts = line.split()
        now = int(parts[0])
        op = parts[1]
        key = parts[2]
        if op == "SET":
            expires[key] = now + int(parts[3])
        else:
            out.append("HIT" if expires.get(key, -1) > now else "MISS")
    return "\n".join(out)


if __name__ == '__main__':
    import sys
    print(solve(sys.stdin.read()))
