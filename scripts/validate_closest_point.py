import sys
import time

if __name__ == "__main__":
    # parse optional args from YAML via runner: --distance-threshold <value>
    distance = None
    argv = sys.argv[1:]
    for i, tok in enumerate(argv):
        if tok == "--distance-threshold" and i + 1 < len(argv):
            distance = argv[i + 1]
            break

    print("Running ValidateClosestPoint", flush=True)
    if distance is not None:
        print(f"Param distance-threshold = {distance}", flush=True)
    time.sleep(1)
    print("Done ValidateClosestPoint", flush=True)
