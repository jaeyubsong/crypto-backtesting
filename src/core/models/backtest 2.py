"""
Backtest configuration and results models.
To be implemented in Phase 2.
"""

from dataclasses import dataclass
from datetime import datetime

from .position import Trade


@dataclass
class BacktestConfig:
    """Configuration for a backtest execution."""

    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    trading_mode: str
    max_leverage: float
    maintenance_margin_rate: float


@dataclass
class BacktestResults:
    """Results from a backtest execution."""

    config: BacktestConfig
    trades: list[Trade]
    portfolio_history: list[dict]
    metrics: dict[str, float]
    status: str
    error_message: str | None = None
