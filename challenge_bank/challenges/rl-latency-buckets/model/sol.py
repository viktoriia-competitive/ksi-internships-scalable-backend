def solve(data: str) -> str:
    nums = list(map(int, data.split()))
    b, n = nums[0], nums[1]
    limits = nums[2:2+b]
    values = nums[2+b:2+b+n]
    counts = [0] * (b + 1)
    import bisect
    for value in values:
        counts[bisect.bisect_left(limits, value)] += 1
    return " ".join(map(str, counts))


if __name__ == '__main__':
    import sys
    print(solve(sys.stdin.read()))
