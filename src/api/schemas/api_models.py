"""
Pydantic schemas for API request/response models.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from src.core.enums import Symbol, Timeframe, TradingMode


class BacktestRequest(BaseModel):
    """Request model for backtest submission."""

    strategy_code: str
    symbol: Symbol = Field(..., description="Trading symbol (BTC or ETH)")
    timeframe: Timeframe = Field(..., description="Candlestick timeframe")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    initial_capital: float = Field(default=10000.0, gt=0, description="Starting capital")
    trading_mode: TradingMode = Field(default=TradingMode.SPOT, description="Trading mode")
    max_leverage: float = Field(default=1.0, ge=1.0, le=125.0, description="Maximum leverage")
    maintenance_margin_rate: float = Field(
        default=0.005,
        ge=0.0,
        le=0.1,
        description="Maintenance margin rate (0-10%)",
    )

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: datetime, info) -> datetime:
        """Validate that end_date is after start_date."""
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v

    @field_validator("max_leverage")
    @classmethod
    def validate_leverage(cls, v: float, info) -> float:
        """Validate leverage based on trading mode."""
        if "trading_mode" in info.data:
            mode = info.data["trading_mode"]
            if not TradingMode.validate_leverage(mode, v):
                max_lev = TradingMode.max_leverage(mode)
                raise ValueError(f"Leverage {v} not valid for {mode} mode (max: {max_lev})")
        return v


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

    symbol: Symbol
    timeframe: Timeframe
    data: list[dict]


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str
    message: str
    details: dict | None = None
    backtest_id: str | None = None
