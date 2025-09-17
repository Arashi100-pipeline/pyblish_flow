import sys
import time

if __name__ == "__main__":
    # parse dynamic pairs like --grass 0 --tree 1
    params = {}
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok.startswith("--") and i + 1 < len(argv):
            key = tok[2:]
            val = argv[i + 1]
            params[key] = val
            i += 2
        else:
            i += 1

    print("Running ValidateIsolatedVertex", flush=True)
    if params:
        for k, v in params.items():
            print(f"Param {k} = {v}", flush=True)
    time.sleep(1)
    print("Done ValidateIsolatedVertex", flush=True)
