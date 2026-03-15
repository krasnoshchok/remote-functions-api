"""
Main application file for Remote Functions Processing API

This module initializes the FastAPI application, sets up metadata
(title, description, version), defines a basic health check endpoint,
and includes the routers containing the business logic for managing server resources.

The application serves as the entry point for the RESTful API.

Routers Included:
- servers: Handles CRUD operations for server resources (defined in app.routers.servers).
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from logging_config import setup_logging
from routers import routes

# Setup logging before anything else
Path("logs").mkdir(parents=True, exist_ok=True)
setup_logging(log_level="INFO", log_file="logs/app.log")

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    logger.info("Application starting up")
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title="Remote Functions Processing API",
    description="RESTful API for processing remote python functions",
    version="1.0.0",
    lifespan=lifespan
)


# Health check endpoint
@app.get("/health", tags=["health"])
def health_check():
    """
    Status check to verify the service is running.

    Returns a simple message indicating the service is operational.
    """
    return {"status": "ok", "message": "Service is running"}


# Include server router
app.include_router(routes.router)


@app.get("/")
def root():
    """
    **Root endpoint** for the Remote Functions Processing API

    Returns:
        dict: A simple dictionary with a welcome message.
    """
    return {"message": "Remote Functions Processing API"}
