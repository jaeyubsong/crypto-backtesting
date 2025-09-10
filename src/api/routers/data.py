"""
Data API endpoints.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/symbols")
async def get_available_symbols():
    """Get list of available trading symbols."""
    return {
        "message": "Get available symbols - to be implemented in Phase 3",
        "status": "not_implemented",
    }


@router.get("/history")
async def get_historical_data():
    """Get historical OHLCV data for charting."""
    return {
        "message": "Get historical data - to be implemented in Phase 3",
        "status": "not_implemented",
    }
