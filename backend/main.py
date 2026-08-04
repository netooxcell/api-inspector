import json
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Optional

import analyzer
import db
from proxy import forward_request, forward_raw

app = FastAPI(title="API Request Inspector")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProxyRequest(BaseModel):
    target_url: str
    method: str = "GET"
    headers: Optional[dict] = None
    body: Optional[Any] = None
    query_params: Optional[dict] = None


class ReplayRequest(BaseModel):
    target_url: Optional[str] = None
    headers: Optional[dict] = None
    body: Optional[Any] = None
    query_params: Optional[dict] = None


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(data, default=str))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@app.on_event("startup")
def on_startup():
    db.init_db()


async def _execute_and_store(record_id: int, method: str, target_url: str,
                              headers: dict, body, query_params: dict):
    result = await forward_request(method, target_url, headers, body, query_params)
    analysis = analyzer.analyze(
        status=result.status,
        headers=result.headers,
        body=result.body,
        target_url=target_url,
        req_headers=headers,
        req_body=body,
        timed_out=result.timed_out,
    )
    db.complete_request(
        record_id, result.status, result.headers, result.body,
        result.duration_ms, analysis,
    )
    record = db.get_request(record_id)
    await manager.broadcast({"type": "request_completed", "data": record})
    return record


@app.post("/proxy")
async def proxy(req: ProxyRequest):
    headers = req.headers or {}
    query_params = req.query_params or {}
    record_id = db.create_pending(req.method, req.target_url, headers, req.body, query_params)
    record = await _execute_and_store(record_id, req.method, req.target_url, headers, req.body, query_params)
    return record


@app.get("/requests")
def get_requests(limit: int = 50, status: str = "all"):
    return db.list_requests(limit=limit, status=status)


@app.get("/requests/{record_id}")
def get_request_by_id(record_id: int):
    record = db.get_request(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return record


@app.post("/requests/{record_id}/replay")
async def replay_request(record_id: int, override: ReplayRequest):
    original = db.get_request(record_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Request not found")

    target_url = override.target_url or original["target_url"]
    headers = override.headers if override.headers is not None else (original.get("req_headers") or {})
    body = override.body if override.body is not None else original.get("req_body")
    query_params = override.query_params if override.query_params is not None else (original.get("req_params") or {})

    new_id = db.create_pending(
        original["method"], target_url, headers, body, query_params, parent_id=record_id,
    )
    record = await _execute_and_store(new_id, original["method"], target_url, headers, body, query_params)
    return record


@app.delete("/requests")
def clear_requests():
    db.clear_all()
    return {"status": "cleared"}


CAPTURE_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
STRIPPED_RESPONSE_HEADERS = {"content-encoding", "content-length", "transfer-encoding", "connection", "date", "server"}


async def _capture_passthrough(full_path: str, request: Request):
    """Transparent reverse proxy: forwards a real client request to UPSTREAM_BASE_URL,
    captures the request/response pair, and returns the real response unchanged so
    the browser sees a normal working site while the traffic gets logged and analyzed."""
    upstream_base = os.environ.get("UPSTREAM_BASE_URL")
    if not upstream_base:
        raise HTTPException(
            status_code=501,
            detail="UPSTREAM_BASE_URL is not set. Add it to backend/.env, e.g. UPSTREAM_BASE_URL=http://localhost:3000",
        )

    upstream_url = f"{upstream_base.rstrip('/')}/{full_path}"
    raw_body = await request.body()
    headers = dict(request.headers)
    query_params = dict(request.query_params)

    try:
        stored_body = json.loads(raw_body) if raw_body else None
    except (json.JSONDecodeError, UnicodeDecodeError):
        stored_body = raw_body.decode("utf-8", errors="replace") if raw_body else None

    record_id = db.create_pending(request.method, upstream_url, headers, stored_body, query_params)

    result = await forward_raw(request.method, upstream_url, headers, raw_body, query_params)
    analysis = analyzer.analyze(
        status=result.status,
        headers=result.headers,
        body=result.body,
        target_url=upstream_url,
        req_headers=headers,
        req_body=stored_body,
        timed_out=result.timed_out,
    )
    db.complete_request(record_id, result.status, result.headers, result.body, result.duration_ms, analysis)
    record = db.get_request(record_id)
    await manager.broadcast({"type": "request_completed", "data": record})

    if result.status is None:
        return Response(
            content=json.dumps({"error": "upstream unreachable or timed out"}),
            status_code=504,
            media_type="application/json",
        )

    response_headers = {k: v for k, v in result.headers.items() if k.lower() not in STRIPPED_RESPONSE_HEADERS}
    return Response(content=result.raw_content, status_code=result.status, headers=response_headers)


@app.api_route("/capture/{full_path:path}", methods=CAPTURE_METHODS)
async def capture_passthrough(full_path: str, request: Request):
    return await _capture_passthrough(full_path, request)


@app.api_route("/capture", methods=CAPTURE_METHODS)
@app.api_route("/capture/", methods=CAPTURE_METHODS)
async def capture_passthrough_root(request: Request):
    return await _capture_passthrough("", request)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=True,
    )
