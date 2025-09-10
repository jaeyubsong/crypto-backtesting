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
        return self.cash + self.unrealized_pnl(current_prices)

    def available_margin(self) -> float:
        """Calculate available margin for new positions."""
        return self.cash

    def used_margin(self) -> float:
        """Calculate total margin used by open positions."""
        return sum(position.margin_used for position in self.positions.values())

    def unrealized_pnl(self, current_prices: dict[str, float]) -> float:
        """Calculate total unrealized PnL from all positions."""
        total_pnl = 0.0
        for position in self.positions.values():
            if position.symbol in current_prices:
                total_pnl += position.unrealized_pnl(current_prices[position.symbol])
        return total_pnl

    def realized_pnl(self) -> float:
        """Calculate total realized PnL from completed trades."""
        return sum(trade.pnl for trade in self.trades)

    def margin_ratio(self, current_prices: dict[str, float]) -> float:
        """Calculate current margin ratio (equity / used_margin)."""
        used = self.used_margin()
        if used == 0:
            return float("inf")  # No positions, infinite margin ratio

        portfolio_value = self.calculate_portfolio_value(current_prices)
        return portfolio_value / used

    def is_margin_call(
        self, current_prices: dict[str, float], margin_call_threshold: float = 0.5
    ) -> bool:
        """Check if portfolio is at risk of margin call."""
        margin_ratio = self.margin_ratio(current_prices)
        if margin_ratio == float("inf"):
            return False  # No positions
        return margin_ratio <= margin_call_threshold

    def add_position(self, position: Position) -> None:
        """Add a new position to the portfolio."""
        self.positions[position.symbol] = position
        self.cash -= position.margin_used

    def close_position(self, symbol: str, close_price: float, fee: float) -> float:
        """Close a position and return realized PnL."""
        if symbol not in self.positions:
            return 0.0

        position = self.positions[symbol]
        unrealized_pnl = position.unrealized_pnl(close_price)
        realized_pnl = unrealized_pnl - fee

        # Release margin and add realized PnL
        self.cash += position.margin_used + realized_pnl

        # Remove position
        del self.positions[symbol]

        return realized_pnl
