"""
Portfolio domain model.
To be implemented in Phase 2.
"""

from dataclasses import dataclass

from .position import Position, Trade


@dataclass
class Portfolio:
    """Portfolio domain model."""

    initial_capital: float
    cash: float
    positions: dict[str, Position]
    trades: list[Trade]
    portfolio_history: list[dict]

    def calculate_portfolio_value(self, current_prices: dict[str, float]) -> float:
        """Calculate total portfolio value including unrealized PnL."""
        # To be implemented in Phase 4
        pass
