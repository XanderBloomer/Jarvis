"""FastAPI application entry point."""

from fastapi import FastAPI

from content_engine.api.routes.hooks import router as hooks_router
from content_engine.api.routes.scripts import router as scripts_router
from content_engine.api.routes.trends import router as trends_router
from content_engine.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Content Engine",
    description="AI-powered content generation system for short-form video",
    version="0.1.0",
)

# Register routers
app.include_router(trends_router, prefix="/api/v1")
app.include_router(hooks_router, prefix="/api/v1")
app.include_router(scripts_router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "environment": settings.app_env}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Content Engine API", "version": "0.1.0"}
