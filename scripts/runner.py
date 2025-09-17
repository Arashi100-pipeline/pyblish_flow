from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception as e:
    print("runner: missing dependency pyyaml; please install with `uv add pyyaml`", file=sys.stderr, flush=True)
    sys.exit(2)

BASE_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: runner.py <path/to/steps.yaml>", file=sys.stderr)
        return 2

    yaml_path = Path(sys.argv[1])
    with yaml_path.open("r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    steps = spec.get("steps") or []
    for step in steps:
        node_id = str(step.get("id"))
        script = step.get("script")
        args = step.get("args") or []
        if not script:
            continue
        script_path = Path(script)
        if not script_path.is_absolute():
            script_path = (BASE_DIR / script).resolve()
        # run the script
        try:
            subprocess.run([sys.executable, str(script_path), *map(str, args)], check=True)
        except subprocess.CalledProcessError as e:
            # still emit an event to unblock client, then stop
            print("EVENT " + json.dumps({"type": "stage", "nodeId": node_id, "status": "failed"}), flush=True)
            print("EVENT " + json.dumps({"type": "done", "status": "failed"}), flush=True)
            return e.returncode
        # stage done
        print("EVENT " + json.dumps({"type": "stage", "nodeId": node_id, "status": "done"}), flush=True)

    # all done
    print("EVENT " + json.dumps({"type": "done", "status": "succeeded"}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

