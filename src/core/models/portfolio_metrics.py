"""
Portfolio metrics and calculations.

This module handles portfolio value calculations, margin ratios,
and performance metrics following the Single Responsibility Principle.
"""

from typing import TYPE_CHECKING

from src.core.enums import Symbol, TradingMode

if TYPE_CHECKING:
    from .portfolio_core import PortfolioCore


class PortfolioMetrics:
    """Portfolio metrics and calculations.

    Handles all portfolio value calculations, margin ratios,
    and related financial metrics.
    """

    def __init__(self, portfolio_core: "PortfolioCore") -> None:
        """Initialize with portfolio core state.

        Args:
            portfolio_core: The portfolio core state to calculate metrics for
        """
        self.core = portfolio_core

    def calculate_portfolio_value(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate total portfolio value based on trading mode.

        - FUTURES: Portfolio Value = Equity = Cash + Unrealized PnL
        - SPOT/MARGIN: Portfolio Value = Cash + Asset Values

        Args:
            current_prices: Current market prices for all symbols

        Returns:
            Total portfolio value
        """
        if self.core.trading_mode == TradingMode.FUTURES:
            # For futures: equity = cash + unrealized PnL
            return self.core.cash + self.core.unrealized_pnl(current_prices)
        else:
            # For spot/margin: add actual position values
            total_value = self.core.cash
            for symbol, position in self.core.positions.items():
                if symbol in current_prices:
                    total_value += position.position_value(current_prices[symbol])
            return total_value

    def margin_ratio(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate current margin ratio (equity / used_margin).

        Args:
            current_prices: Current market prices for calculating unrealized PnL

        Returns:
            Margin ratio. Returns infinity if no positions are open.
        """
        used = self.core.used_margin()
        if used == 0:
            return float("inf")  # No positions, infinite margin ratio

        # Equity = cash + unrealized PnL (not total portfolio value)
        equity = self.core.cash + self.core.unrealized_pnl(current_prices)
        return equity / used

    def is_margin_call(
        self, current_prices: dict[Symbol, float], margin_call_threshold: float = 0.5
    ) -> bool:
        """Check if portfolio is at risk of margin call.

        Args:
            current_prices: Current market prices
            margin_call_threshold: Threshold for margin call (default 50%)

        Returns:
            True if margin call risk exists
        """
        margin_ratio = self.margin_ratio(current_prices)
        if margin_ratio == float("inf"):
            return False  # No positions
        return margin_ratio <= margin_call_threshold

    def get_margin_ratio(self) -> float:
        """Get current margin ratio for API compatibility.

        Returns:
            Margin usage ratio (0 for spot trading).
        """
        # For spot trading, return 0 (no margin used)
        if self.core.trading_mode == TradingMode.SPOT:
            return 0.0

        # For futures/margin, calculate margin usage
        total_margin = self.core.used_margin()
        if total_margin == 0:
            return 0.0
        return total_margin / self.core.initial_capital

    def get_position_size(self, symbol: Symbol) -> float:
        """Get current position size for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position size. Positive for long, negative for short, 0 if no position.
        """
        from src.core.utils.validation import validate_symbol

        symbol = validate_symbol(symbol)
        position = self.core.positions.get(symbol)
        return position.size if position else 0.0

    def get_leverage(self, symbol: Symbol) -> float:
        """Get current leverage for a position.

        Args:
            symbol: Trading symbol

        Returns:
            Position leverage (0 if no position).
        """
        from src.core.utils.validation import validate_symbol

        symbol = validate_symbol(symbol)
        position = self.core.positions.get(symbol)
        return position.leverage if position else 0.0

    def get_unrealized_pnl(self, symbol: Symbol, current_price: float) -> float:
        """Get unrealized PnL for a specific position.

        Args:
            symbol: Trading symbol
            current_price: Current market price

        Returns:
            Unrealized PnL (0 if no position).
        """
        from src.core.utils.validation import validate_positive, validate_symbol

        symbol = validate_symbol(symbol)
        current_price = validate_positive(current_price, "current_price")
        position = self.core.positions.get(symbol)
        return position.unrealized_pnl(current_price) if position else 0.0
