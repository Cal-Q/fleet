#!/usr/bin/env python3
"""
api/app.py — Japan Studies & Mastery Platform (japan.calq.it)
Unified application entrypoint for Daily Study, Anki SRS, Tampermonkey Bridge, and MEXT Drills.
Strictly <= 200 lines invariant.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from api.routes.study_routes import router as study_router
from api.routes.srs_routes import router as srs_router
from api.routes.relay_routes import router as relay_router
from api.routes.exam_routes import router as exam_router
from api.routes.career_routes import router as career_router
from api.routes.system_routes import router as system_router
from api.routes.style_routes import router as style_router
from api.routes.curriculum_routes import router as curriculum_router
from api.routes.anki_web_routes import router as anki_web_router
from api.routes.anki_fsrs_routes import router as anki_fsrs_router
from api.routes.anki_log_routes import router as anki_log_router

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
MEDIA_DIR = os.path.join(BASE_DIR, ".local/share/Anki2/User 1/collection.media")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

app = FastAPI(
    title="Japan • Platform & Studies",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://japan.calq.it",
        "https://bunpro.jp",
        "https://calq.it",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cache_control_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith("sw_anki.js") or path.endswith("sw.js"):
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    elif path.startswith("/media/"):
        response.headers["Cache-Control"] = "public, max-age=604800, stale-while-revalidate=86400"
    else:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR, follow_symlink=True), name="static")

if os.path.exists(PUBLIC_DIR):
    app.mount("/scripts", StaticFiles(directory=PUBLIC_DIR), name="scripts")

if os.path.exists(MEDIA_DIR):
    app.mount("/media", StaticFiles(directory=MEDIA_DIR, follow_symlink=True), name="media")

app.include_router(study_router)
app.include_router(srs_router)
app.include_router(relay_router)
app.include_router(exam_router)
app.include_router(career_router)
app.include_router(system_router)
app.include_router(style_router)
app.include_router(curriculum_router)
app.include_router(anki_web_router)
app.include_router(anki_fsrs_router)
app.include_router(anki_log_router)


@app.api_route("/sw_anki.js", methods=["GET", "HEAD"])
@app.api_route("/sw.js", methods=["GET", "HEAD"])
def get_service_worker():
    sw_path = os.path.join(STATIC_DIR, "sw_anki.js")
    headers = {
        "Service-Worker-Allowed": "/",
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
    }
    return FileResponse(sw_path, headers=headers, media_type="application/javascript")


@app.api_route("/manifest_anki.json", methods=["GET", "HEAD"])
@app.api_route("/manifest.json", methods=["GET", "HEAD"])
def get_manifest():
    mf_path = os.path.join(STATIC_DIR, "manifest_anki.json")
    return FileResponse(mf_path, media_type="application/manifest+json")


@app.get("/r", response_class=PlainTextResponse)
@app.get("/r.sh", response_class=PlainTextResponse)
@app.get("/redmi", response_class=PlainTextResponse)
@app.get("/k", response_class=PlainTextResponse)
def get_redmi_setup():
    script_path = os.path.join(PUBLIC_DIR, "redmi.sh")
    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            return f.read()
    return "#!/bin/bash\necho 'Script not found'\n"


@app.api_route("/", methods=["GET", "HEAD"])
def index_page(request: Request):
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    if not os.path.exists(index_file):
        return HTMLResponse("<h1>Template non trovato</h1>", status_code=500)
    return templates.TemplateResponse(request=request, name="index.html")



def main():
    import uvicorn
    uvicorn.run("api.app:app", host="127.0.0.1", port=3033, reload=False)


if __name__ == "__main__":
    main()
