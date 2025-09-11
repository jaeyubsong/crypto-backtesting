"""
Portfolio domain model.
To be implemented in Phase 2.
"""

from dataclasses import dataclass

from src.core.enums import Symbol
from src.core.exceptions.backtest import (
    InsufficientFundsError,
    PositionNotFoundError,
    ValidationError,
)

from .position import Position, Trade


@dataclass
class Portfolio:
    """Portfolio domain model."""

    initial_capital: float
    cash: float
    positions: dict[Symbol, Position]
    trades: list[Trade]
    portfolio_history: list[dict]

    def calculate_portfolio_value(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate total portfolio value including positions and unrealized PnL."""
        total_value = self.cash
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                # Add position value plus unrealized PnL
                total_value += position.position_value(current_prices[symbol])
        return total_value

    def available_margin(self) -> float:
        """Calculate available margin for new positions."""
        return self.cash

    def used_margin(self) -> float:
        """Calculate total margin used by open positions."""
        return sum(position.margin_used for position in self.positions.values())

    def unrealized_pnl(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate total unrealized PnL from all positions."""
        total_pnl = 0.0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                total_pnl += position.unrealized_pnl(current_prices[symbol])
        return total_pnl

    def realized_pnl(self) -> float:
        """Calculate total realized PnL from completed trades."""
        return sum(trade.pnl for trade in self.trades)

    def margin_ratio(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate current margin ratio (equity / used_margin)."""
        used = self.used_margin()
        if used == 0:
            return float("inf")  # No positions, infinite margin ratio

        # Equity = cash + unrealized PnL (not total portfolio value)
        equity = self.cash + self.unrealized_pnl(current_prices)
        return equity / used

    def is_margin_call(
        self, current_prices: dict[Symbol, float], margin_call_threshold: float = 0.5
    ) -> bool:
        """Check if portfolio is at risk of margin call."""
        margin_ratio = self.margin_ratio(current_prices)
        if margin_ratio == float("inf"):
            return False  # No positions
        return margin_ratio <= margin_call_threshold

    def add_position(self, position: Position) -> None:
        """Add a new position to the portfolio."""
        # Validate inputs
        if not isinstance(position, Position):
            raise ValidationError("Position must be a valid Position instance")
        if not position.symbol or not isinstance(position.symbol, Symbol):
            raise ValidationError("Position symbol must be a valid Symbol enum")
        if position.leverage <= 0:
            raise ValidationError("Position leverage must be positive")
        if position.margin_used < 0:
            raise ValidationError("Position margin_used must be non-negative")
        if position.margin_used > self.cash:
            raise InsufficientFundsError(
                required=position.margin_used, available=self.cash, operation="opening position"
            )

        self.positions[position.symbol] = position
        self.cash -= position.margin_used

    def close_position(self, symbol: Symbol, close_price: float, fee: float) -> float:
        """Close a position and return realized PnL."""
        # Validate inputs
        if not symbol or not isinstance(symbol, Symbol):
            raise ValidationError("Symbol must be a valid Symbol enum")
        if close_price <= 0:
            raise ValidationError("Close price must be positive")
        if fee < 0:
            raise ValidationError("Fee must be non-negative")

        if symbol not in self.positions:
            raise PositionNotFoundError(symbol.value)

        position = self.positions[symbol]
        unrealized_pnl = position.unrealized_pnl(close_price)
        realized_pnl = unrealized_pnl - fee

        # Release margin and add realized PnL
        self.cash += position.margin_used + realized_pnl

        # Remove position
        del self.positions[symbol]

        return realized_pnl
