"""FastAPI backend — endpoint command + WebSocket log real-time."""
import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.orchestrator import AGENTS, Orchestrator
from backend.tools.registry import WORKSPACE

app = FastAPI(title="Web Command Center")
orch = Orchestrator()

# --- WebSocket clients ---
clients: set[WebSocket] = set()


async def broadcast(msg: str):
    dead = []
    for ws in clients:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)


_loop = None  # di-set saat startup


def log_fn(msg: str):
    """Log dari orchestrator thread -> broadcast via event loop utama."""
    line = json.dumps({"t": "log", "msg": msg}, ensure_ascii=False)
    if _loop is not None:
        _loop.call_soon_threadsafe(asyncio.ensure_future, broadcast(line))


orch.log = log_fn


class Command(BaseModel):
    objective: str
    pipeline: list[str] | None = None  # None = auto-plan oleh LLM


@app.on_event("startup")
async def _startup():
    global _loop
    _loop = asyncio.get_running_loop()


@app.get("/")
async def index():
    return FileResponse("frontend/index.html")


@app.get("/app.js")
async def app_js():
    return FileResponse("frontend/app.js")


@app.get("/api/agents")
async def agents():
    return {k: {"role": v["role"], "tools": v["tools"]} for k, v in AGENTS.items()}


@app.post("/api/command")
async def command(cmd: Command):
    pipeline = cmd.pipeline or orch.auto_plan(cmd.objective)
    asyncio.get_event_loop().run_in_executor(None, orch.run_pipeline, cmd.objective, pipeline)
    return {"status": "started", "pipeline": pipeline}


@app.get("/api/workspace")
async def workspace():
    files = [str(p.relative_to(WORKSPACE)) for p in WORKSPACE.rglob("*") if p.is_file()]
    return {"files": files}


@app.get("/api/workspace/file")
async def ws_file(name: str):
    p = (WORKSPACE / name).resolve()
    if not str(p).startswith(str(WORKSPACE)) or not p.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(p)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        clients.discard(ws)
