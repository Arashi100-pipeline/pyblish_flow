from __future__ import annotations

import sys
import time


def main() -> int:
    # This demo script simulates creating a cube, waits 1s, then exits.
    print("[TestCreateCube] start", flush=True)
    time.sleep(1)
    print("[TestCreateCube] created cube", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

