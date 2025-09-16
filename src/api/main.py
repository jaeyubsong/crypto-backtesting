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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
