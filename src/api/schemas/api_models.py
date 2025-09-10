"""
Pydantic schemas for API request/response models.
"""

from pydantic import BaseModel


class BacktestRequest(BaseModel):
    """Request model for backtest submission."""

    strategy_code: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_capital: float = 10000.0
    trading_mode: str = "spot"
    max_leverage: float = 1.0
    maintenance_margin_rate: float = 0.005


class BacktestResponse(BaseModel):
    """Response model for backtest submission."""

    backtest_id: str
    status: str
    message: str


class BacktestResults(BaseModel):
    """Response model for backtest results."""

    backtest_id: str
    status: str
    config: dict | None = None
    metrics: dict | None = None
    trades: list[dict] | None = None
    portfolio_history: list[dict] | None = None
    error_message: str | None = None


class SymbolsResponse(BaseModel):
    """Response model for available symbols."""

    symbols: list[str]
    trading_modes: list[str]


class HistoricalData(BaseModel):
    """Response model for historical data."""

    symbol: str
    timeframe: str
    data: list[dict]


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str
    message: str
    details: dict | None = None
    backtest_id: str | None = None
