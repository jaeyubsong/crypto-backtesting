"""
Backtest configuration and results models.
To be implemented in Phase 2.
"""

from dataclasses import dataclass
from datetime import datetime

from src.core.enums import Symbol, Timeframe, TradingMode

from .position import Trade


@dataclass
class BacktestConfig:
    """Configuration for a backtest execution."""

    symbol: Symbol
    timeframe: Timeframe
    start_date: datetime
    end_date: datetime
    initial_capital: float
    trading_mode: TradingMode
    max_leverage: float
    maintenance_margin_rate: float

    def is_valid_date_range(self) -> bool:
        """Validate that end_date is after start_date."""
        return self.end_date > self.start_date

    def duration_days(self) -> int:
        """Calculate duration of backtest in days."""
        return (self.end_date - self.start_date).days

    def is_valid_leverage(self) -> bool:
        """Validate leverage is within reasonable bounds."""
        return TradingMode.validate_leverage(self.trading_mode, self.max_leverage)

    def is_valid_capital(self) -> bool:
        """Validate initial capital is positive."""
        return self.initial_capital > 0

    def is_valid_margin_rate(self) -> bool:
        """Validate maintenance margin rate is reasonable."""
        return 0.0 <= self.maintenance_margin_rate <= 0.1  # 0% to 10%

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            "symbol": self.symbol.value,
            "timeframe": self.timeframe.value,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_capital": self.initial_capital,
            "trading_mode": self.trading_mode.value,
            "max_leverage": self.max_leverage,
            "maintenance_margin_rate": self.maintenance_margin_rate,
        }


@dataclass
class BacktestResults:
    """Results from a backtest execution."""

    config: BacktestConfig
    trades: list[Trade]
    portfolio_history: list[dict]
    metrics: dict[str, float]
    status: str
    error_message: str | None = None

    def performance_summary(self) -> dict:
        """Get a summary of key performance metrics."""
        if not self.portfolio_history:
            return {}

        initial_value = self.portfolio_history[0].get("portfolio_value", 0.0)
        final_value = self.portfolio_history[-1].get("portfolio_value", 0.0)

        return {
            "initial_value": initial_value,
            "final_value": final_value,
            "total_return": self.metrics.get("total_return", 0.0),
            "duration_days": self.config.duration_days(),
        }

    def is_profitable(self) -> bool:
        """Check if the backtest was profitable."""
        return self.metrics.get("total_return", 0.0) > 0.0

    def to_dict(self) -> dict:
        """Convert results to dictionary."""
        return {
            "config": self.config.to_dict(),
            "status": self.status,
            "error_message": self.error_message,
            "metrics": self.metrics,
            "trades": [
                {
                    "timestamp": trade.timestamp.isoformat(),
                    "symbol": trade.symbol,
                    "action": trade.action,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "leverage": trade.leverage,
                    "fee": trade.fee,
                    "position_type": trade.position_type,
                    "pnl": trade.pnl,
                    "margin_used": trade.margin_used,
                }
                for trade in self.trades
            ],
            "portfolio_history": self.portfolio_history,
        }
