from __future__ import annotations

import asyncio
import json
import sys
import uuid
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"

# Map node label -> script path (relative to repo root)
REGISTRY: dict[str, str] = {
    "CollectInstances": str(SCRIPTS_DIR / "collect_instances.py"),
    "ValidateClosestPoint": str(SCRIPTS_DIR / "validate_closest_point.py"),
    "ValidateIsolatedVertex": str(SCRIPTS_DIR / "validate_isolated_vertex.py"),
    "ExtractFBXSimple": str(SCRIPTS_DIR / "extract_fbx_simple.py"),
    "TestCreateCube": str(SCRIPTS_DIR / "test_create_cube.py"),
}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # dev origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# jobId -> asyncio.Queue[str]
QUEUES: dict[str, asyncio.Queue[str]] = {}


@app.post("/runs")
async def create_run(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")

    flow = body.get("flow") or {}
    nodes = {str(n.get("id")): n for n in (flow.get("nodes") or [])}
    edges = flow.get("edges") or []

    # simple chain order: follow first outgoing edge starting from indegree==0
    indeg: dict[str, int] = {nid: 0 for nid in nodes}
    adj: dict[str, list[str]] = {nid: [] for nid in nodes}
    for e in edges:
        s = str(e.get("source"))
        t = str(e.get("target"))
        if s not in adj:
            adj[s] = []
        adj[s].append(t)
        if t not in indeg:
            indeg[t] = 0
        indeg[t] += 1
        if s not in indeg:
            indeg[s] = indeg.get(s, 0)

    start = None
    for k, v in indeg.items():
        if v == 0:
            start = k
            break

    order: list[str] = []
    seen: set[str] = set()
    cur = start
    while cur and cur not in seen:
        order.append(cur)
        seen.add(cur)
        outs = adj.get(cur) or []
        cur = outs[0] if outs else None

    # Build YAML string (no PyYAML required here)
    params = (body.get("params") or {})
    cp = (params.get("closestPointParams") or {})
    iv = (params.get("isolatedVertexParams") or [])

    lines: list[str] = ["version: 1", "steps:"]
    for nid in order:
        node = nodes.get(nid)
        if not node:
            continue
        label = node.get("label") or node.get("data", {}).get("label")
        script = REGISTRY.get(str(label))
        if not script:
            # skip unknown nodes
            continue
        # args mapping based on node label
        args: list[str] = []
        if label == "ValidateClosestPoint":
            dt = cp.get("distanceThreshold")
            if dt:
                args += ["--distance-threshold", str(dt)]
        elif label == "ValidateIsolatedVertex":
            try:
                for item in iv:
                    name = str(item.get("name")).strip()
                    index = item.get("index")
                    if name and index is not None:
                        args += [f"--{name.lower()}", str(index)]
            except Exception:
                pass

        lines.append(f"  - id: \"{nid}\"")
        lines.append(f"    name: \"{label}\"")
        lines.append(f"    script: \"{script.replace('\\', '/') }\"")
        if args:
            # YAML sequence
            lines.append("    args:")
            for a in args:
                lines.append(f"      - \"{str(a).replace('\\\\', '/')}\"")
        else:
            lines.append("    args: []")

    if len(lines) <= 2:
        raise HTTPException(status_code=400, detail="no runnable steps")

    # Write YAML to a temporary file (keep on disk for inspection)
    with NamedTemporaryFile('w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")
        yaml_path = f.name

    job_id = str(uuid.uuid4())
    queue: asyncio.Queue[str] = asyncio.Queue()
    QUEUES[job_id] = queue

    # First line: show YAML path in logs panel
    queue.put_nowait(_sse("log", {"line": f"[YAML] {yaml_path}"}))

    # Spawn runner as a subprocess and forward its EVENT lines as SSE payloads
    asyncio.create_task(_run_job(job_id, yaml_path, queue))

    return {"jobId": job_id}


async def _run_job(job_id: str, yaml_path: str, queue: asyncio.Queue[str]):
    # Capture the running loop and pass it to the worker thread so we can call_soon_threadsafe on Windows
    loop = asyncio.get_running_loop()

    def run_blocking(loop_obj: asyncio.AbstractEventLoop) -> int:
        proc = subprocess.Popen(
            [sys.executable, str(SCRIPTS_DIR / "runner.py"), yaml_path],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\r\n")
            if line.startswith("EVENT "):
                payload = line[6:]
                try:
                    evt = json.loads(payload)
                except Exception:
                    evt = None
                if evt:
                    if evt.get("type") == "stage":
                        loop_obj.call_soon_threadsafe(
                            queue.put_nowait,
                            _sse("stage", {"jobId": job_id, "nodeId": evt.get("nodeId"), "status": evt.get("status", "done")}),
                        )
                    elif evt.get("type") == "done":
                        loop_obj.call_soon_threadsafe(
                            queue.put_nowait,
                            _sse("done", {"status": evt.get("status", "succeeded")}),
                        )
            else:
                loop_obj.call_soon_threadsafe(
                    queue.put_nowait, _sse("log", {"line": line})
                )
        return proc.wait()

    rc = await asyncio.to_thread(run_blocking, loop)
    # Ensure done event if not already emitted
    await queue.put(_sse("done", {"status": "succeeded" if rc == 0 else "failed"}))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/runs/{job_id}/events")
async def stream_events(job_id: str):
    if job_id not in QUEUES:
        raise HTTPException(status_code=404, detail="job not found")

    queue = QUEUES[job_id]

    async def gen():
        while True:
            msg = await queue.get()
            yield msg
            # Stop after done event
            if msg.startswith("event: done"):
                break

        # cleanup
        try:
            del QUEUES[job_id]
        except KeyError:
            pass

    return StreamingResponse(gen(), media_type="text/event-stream")

