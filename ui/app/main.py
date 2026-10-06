import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ui.app.routes.auth import router as auth_router
from ui.app.routes.pages import router as pages_router
from ui.app.routes.requests import router as requests_router
from ui.app.routes.zones import router as zones_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

app = FastAPI(title="DNS Self-Service Automation Platform")

app.mount("/static", StaticFiles(directory="ui/app/static"), name="static")
app.include_router(auth_router)
app.include_router(pages_router)
app.include_router(zones_router)
app.include_router(requests_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
