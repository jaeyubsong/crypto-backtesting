"""
FastAPI main application for crypto backtesting platform.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import backtest, data

app = FastAPI(
    title="Crypto Backtesting API",
    version="1.0.0",
    description="API for crypto quantitative trading strategy backtesting",
)

# Production-ready CORS configuration
# For development, use environment-specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",  # Replace with actual production domain
        "https://api.yourdomain.com",  # API subdomain if used
        "http://localhost:3000",  # Development frontend (React/Vue/etc)
        "http://localhost:8080",  # Alternative development port
    ],
    allow_credentials=False,  # Disable credentials for security
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specific methods only
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],  # Specific headers only
)

app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(data.router, prefix="/api/data", tags=["data"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning API information."""
    return {"message": "Crypto Backtesting API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
