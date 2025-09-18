from __future__ import annotations

import os
import sys
import time


def main() -> int:
    host = os.environ.get("MAYA_RPYC_HOST", "127.0.0.1")
    port = int(os.environ.get("MAYA_RPYC_PORT", "18861"))

    print(f"[TestCreateCube] connecting RPyC maya at {host}:{port}", flush=True)

    try:
        import rpyc  # type: ignore
    except Exception as e:
        print("[TestCreateCube] ERROR: missing dependency 'rpyc' in this environment.", flush=True)
        print("Hint: run inside server env: 'uv add rpyc' (in server directory)", flush=True)
        return 2

    try:
        conn = rpyc.classic.connect(host, port)
    except Exception as e:
        print(f"[TestCreateCube] ERROR: cannot connect to Maya RPyC at {host}:{port}: {e}", flush=True)
        return 3

    try:
        maya = conn.modules.maya
        # Ensure cmds exists
        _ = maya.cmds.about(api=True)
        maya.cmds.polyCube(name="TestCube")
        print("[TestCreateCube] created cube via maya.cmds.polyCube()", flush=True)
    except Exception as e:
        print(f"[TestCreateCube] ERROR while calling maya: {e}", flush=True)
        return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

