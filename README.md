# pyblish_flow

An interactive demo that lets you design a simple validation pipeline in the browser (Vue Flow), send it to a FastAPI backend, and run Python scripts with real‑time progress via Server‑Sent Events (SSE).

- Frontend: Vue 3 + TypeScript + Vite + @vue-flow/core
- Backend: FastAPI (uvicorn), Python runner spawning demo scripts
- Realtime: SSE streaming of logs/stages to a floating "Run Logs" panel
- Windows‑friendly: subprocess implemented with `subprocess.Popen` + `asyncio.to_thread`

## Features
- Manual connect between nodes; chain execution order inferred from the first outgoing edge.
- Alt + click on an edge to disconnect that edge (quick delete).
- "Reset" resets node colors and animations (does not remove edges).
- Parameters UI for selected nodes (closest‑point threshold; isolated‑vertex rows).
- On Run, backend generates a YAML into the system temp directory and prints its full path as the first log line.
- Nodes turn green as each stage completes; the next edge animates during transition.

## Quickstart (Windows)
Prerequisites:
- Node.js + npm
- Python (3.10+ recommended)
- uv (Python package manager)

One‑command startup (opens two terminals and the browser):

````powershell
# from repo root
npm run dev:all
# or
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
````

Manual startup:

````powershell
# Backend
cd server
uv sync
uv run uvicorn main:app --reload --port 8000

# Frontend (another terminal)
cd ..
npm ci
npm run dev
````

Open http://localhost:5173.

## How to use
1) Manually draw a single chain (e.g., 1 → 2 → 3 → 4).
2) Click a node to open the parameters drawer (supported on nodes 2 and 3).
3) Click "Run".
   - The first line in "Run Logs" shows the YAML file path (in your OS temp folder).
   - Script logs and stage updates stream in real time.
4) To disconnect a specific edge: hold Alt (Option on macOS) and click the edge.
5) "Reset" restores node colors/animations (does not delete edges).

## YAML generation & lifecycle
- Generated on each "Run" from the current graph and parameters.
- Written to a temporary file with a random name (e.g., `C:\Users\\<you>\\AppData\\Local\\Temp\\tmpxxxx.yaml`).
- The path is emitted as the first SSE log line: `[YAML] <full_path>`.
- The backend spawns `python scripts/runner.py <yaml_path>`; the runner reads and executes steps sequentially.
- The temp file is kept (delete=False) so you can inspect it after runs.

Minimal YAML example the runner understands:

````yaml
version: 1
steps:
  - id: "1"
    name: "CollectInstances"
    script: "scripts/collect_instances.py"
    args: []
  - id: "2"
    name: "ValidateClosestPoint"
    script: "scripts/validate_closest_point.py"
    args:
      - "--distance-threshold"
      - "10cm"
````

## Project layout
- `src/` – Vue app and Flow UI (Alt+click edge delete; Run Logs panel)
- `server/` – FastAPI app and SSE bridge (CORS allows localhost:5173 and 127.0.0.1:5173)
- `scripts/` – Demo Python scripts and the `runner.py`
- `start.ps1` – Windows helper to install deps (if missing) and start both FE/BE

## Notes
- Backend captures child process stdout and forwards it as SSE; backend console will primarily show HTTP access logs.
  If you prefer mirroring script logs to backend console as well, this can be added behind a flag.
- This is a demo; concurrency and multi‑job isolation are intentionally simplified.

## License
MIT. See [LICENSE](./LICENSE) for details.
