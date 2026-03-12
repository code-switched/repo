"""FastAPI application."""

from fastapi import FastAPI

from .config import load_web_config

# Load web configuration
web_config = load_web_config()

app = FastAPI(title="repo")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"status": "ok"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"healthy": True}
