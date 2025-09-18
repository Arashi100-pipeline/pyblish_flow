import argparse
import os
from pathlib import Path

import rpyc


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute a target script inside Maya main thread via RPyC + runpy")
    default_target = Path(__file__).resolve().parent / "open_pyblish.py"
    parser.add_argument("--script", default=str(default_target), help="Target script path to execute in Maya")
    args = parser.parse_args()

    host = os.getenv("MAYA_RPYC_HOST", "127.0.0.1")
    port = int(os.getenv("MAYA_RPYC_PORT", "18861"))
    target = str(Path(args.script).resolve())

    # Connect to Maya's RPyC ClassicService
    conn = rpyc.classic.connect(host, port)

    # Run the entire target script in Maya's UI/main thread using runpy.run_path
    remote_code = (
        "import runpy\n"
        f"runpy.run_path(r'{target}', run_name='__main__')\n"
    )
    conn.modules.maya.utils.executeInMainThreadWithResult(remote_code)
    print("[TestRunScripts] executed on Maya main thread:", target)


if __name__ == "__main__":
    main()

