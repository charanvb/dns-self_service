from fastapi import FastAPI

from ui.app.routes.auth import router as auth_router

app = FastAPI(title="DNS Self-Service Automation Platform")

app.include_router(auth_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
