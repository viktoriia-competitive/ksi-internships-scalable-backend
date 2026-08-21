"""Consume CPU long enough for the fixture budget to interrupt the process."""

from time import perf_counter

deadline = perf_counter() + 30.0
accumulator = 0xC0FFEE
while perf_counter() < deadline:
    accumulator = ((accumulator << 5) ^ (accumulator >> 2) ^ 0x9E3779B9) & 0xFFFFFFFF
print(accumulator)
