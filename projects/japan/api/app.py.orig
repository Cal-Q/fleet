#!/usr/bin/env python3
"""
api/app.py — Japan Studies & Mastery Platform (japan.calq.it)
Unified application entrypoint for Daily Study, Anki SRS, Tampermonkey Bridge, and MEXT Drills.
Strictly <= 200 lines invariant.
"""

import os
import sys

BASE_DIR = "/opt/japan"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cache_control_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR, follow_symlink=True), name="static")

if os.path.exists(PUBLIC_DIR):
    app.mount("/scripts", StaticFiles(directory=PUBLIC_DIR), name="scripts")

app.include_router(study_router)
app.include_router(srs_router)
app.include_router(relay_router)
app.include_router(exam_router)
app.include_router(career_router)
app.include_router(system_router)
app.include_router(style_router)
app.include_router(curriculum_router)


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
