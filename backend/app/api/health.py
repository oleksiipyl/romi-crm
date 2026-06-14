from fastapi import APIRouter

from app.schemas.ai_responder import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="romi-crm-backend", version="0.1.0")
