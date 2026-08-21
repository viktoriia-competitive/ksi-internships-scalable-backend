"""Block without CPU work so the wall-clock guard is the limiting signal."""

from threading import Event

Event().wait(timeout=30.0)
print("wall-clock guard did not stop the fixture")
