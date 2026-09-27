from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.core.db.models  # noqa: F401 — register ORM mappers
from app.core.config.settings import get_settings
from app.features.auth.router import router as auth_router
from app.features.chat.router import router as chat_router
from app.features.technicians.router import router as technicians_router
from app.features.tickets.router import router as tickets_router

load_dotenv()

app = FastAPI(
    title="Firefight",
    description="BMS telemetry and incident coordination API",
    version="0.1.0",
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tickets_router)
app.include_router(technicians_router)
app.include_router(chat_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
