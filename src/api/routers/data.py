"""
Data API endpoints.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/symbols")
async def get_available_symbols() -> dict[str, list[str]]:
    """Get list of available trading symbols."""
    return {
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "trading_modes": ["spot", "futures"],
    }


@router.get("/history")
async def get_historical_data() -> dict[str, str]:
    """Get historical OHLCV data for charting."""
    return {
        "message": "Get historical data - to be implemented in Phase 3",
        "status": "not_implemented",
    }
