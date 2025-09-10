"""
Backtest API endpoints.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/")
async def submit_backtest():
    """Submit a new backtest for execution."""
    return {
        "message": "Backtest endpoint - to be implemented in Phase 6",
        "status": "not_implemented",
    }


@router.get("/{backtest_id}")
async def get_backtest_results(backtest_id: str):
    """Get backtest results by ID."""
    return {
        "message": f"Get backtest results for {backtest_id} - to be implemented in Phase 6",
        "status": "not_implemented",
    }
