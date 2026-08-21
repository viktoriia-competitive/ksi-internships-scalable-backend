# Allocate ~256 MiB — should MEMORY_LIMIT under a small cgroup cap (e.g. 32 MB).
# Memory-pressure fixture; run only with an enforced memory cap.
blob = bytearray(256 * 1024 * 1024)
blob[0] = 1
print(len(blob))
