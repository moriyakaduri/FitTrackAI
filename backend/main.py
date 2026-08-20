"""FastAPI composition root: register MVC and CQRS routers."""

from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.cqrs.commands import router as commands_router
from backend.cqrs.queries import router as queries_router
from backend.database import init_database
from backend.mvc.controllers.ai import router as ai_router
from backend.mvc.controllers.auth import router as auth_router


app = FastAPI(
    title="FitTrack AI API - Lev Academic Center",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_database()

app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(commands_router)
app.include_router(queries_router)


@app.get("/")
def root_status() -> Dict[str, str]:
    return {"status": "FitTrack AI API is running", "version": "2.0.0"}
