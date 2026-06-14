import logging

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.ai_responder import router as ai_responder_router
from app.config import get_settings

settings = get_settings()

logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="ROMI CRM API",
    description="Glass repair CRM — AI Lead Responder (Module 10)",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(ai_responder_router)
