"""Authenticated loopback API. Never enabled implicitly; no LAN binding."""

import secrets
import threading
from typing import Literal
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from .engine import Worker


class AddRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=100)
    engine: Literal["auto", "http", "yt-dlp"] = "auto"
    quality: Literal["best", "1080", "720", "480", "360", "mp4"] = "best"


def create_app(store, token: str):
    if len(token) < 32:
        raise ValueError("API token must have at least 32 characters")

    def authorize(authorization: str = Header(default="")):
        if not secrets.compare_digest(authorization, "Bearer " + token):
            raise HTTPException(401, "Authentication required")

    app = FastAPI(
        title="FB MultiEngine local API",
        version="0.2.0a1",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        dependencies=[Depends(authorize)],
    )
    worker = Worker(store)
    guard = threading.Lock()
    thread = None

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(
            status_code=422,
            content={"error": "Invalid request; sensitive inputs omitted"},
        )

    @app.get("/health")
    def health():
        return {"status": "ready", "local_only": True, "remote_engines": False}

    @app.get("/openapi.json")
    def schema():
        return app.openapi()

    @app.get("/jobs")
    def jobs():
        return store.rows()

    @app.post("/jobs")
    def add(body: AddRequest):
        try:
            return {
                "ids": [store.enqueue(u, body.engine, body.quality) for u in body.urls]
            }
        except Exception:
            raise HTTPException(400, "URL rejected or storage unavailable") from None

    @app.post("/jobs/{job_id}/{action}")
    def control(job_id: int, action: Literal["pause", "resume", "cancel"]):
        try:
            store.job(job_id)
        except ValueError:
            raise HTTPException(404, "Unknown job") from None
        getattr(store, action)(job_id)
        return {"status": action}

    @app.post("/run")
    def run():
        nonlocal thread
        with guard:
            if thread and thread.is_alive():
                return {"status": "running"}

            def work():
                try:
                    worker.run()
                except RuntimeError:
                    store.event(None, "worker_busy", "Another worker owns this queue")

            thread = threading.Thread(target=work, daemon=True)
            thread.start()
        return {"status": "started"}

    return app
