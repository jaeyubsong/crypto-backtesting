"""
Portfolio metrics and calculations.

This module handles portfolio value calculations, margin ratios,
and performance metrics following the Single Responsibility Principle.
"""

from collections.abc import Mapping
from decimal import Decimal
from typing import TYPE_CHECKING

from src.core.enums import Symbol, TradingMode
from src.core.types.financial import to_decimal

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

    def calculate_portfolio_value(self, current_prices: Mapping[Symbol, Decimal]) -> Decimal:
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
            cash_decimal = to_decimal(self.core.cash)
            unrealized_pnl_decimal = to_decimal(self.core.unrealized_pnl(current_prices))
            return cash_decimal + unrealized_pnl_decimal
        else:
            # For spot/margin: add actual position values
            total_value = to_decimal(self.core.cash)
            for symbol, position in self.core.positions.items():
                if symbol in current_prices:
                    position_value = to_decimal(position.position_value(current_prices[symbol]))
                    total_value += position_value
            return total_value

    def margin_ratio(self, current_prices: Mapping[Symbol, Decimal]) -> Decimal:
        """Calculate current margin ratio (equity / used_margin).

        Args:
            current_prices: Current market prices for calculating unrealized PnL

        Returns:
            Margin ratio. Returns very large number if no positions are open.
        """
        used = self.core.used_margin()
        if used == 0:
            return Decimal("999999999")  # No positions, very high margin ratio

        # Equity = cash + unrealized PnL (not total portfolio value)
        cash_decimal = to_decimal(self.core.cash)
        unrealized_pnl_decimal = to_decimal(self.core.unrealized_pnl(current_prices))
        used_decimal = to_decimal(used)
        equity = cash_decimal + unrealized_pnl_decimal
        return equity / used_decimal

    def is_margin_call(
        self,
        current_prices: Mapping[Symbol, Decimal],
        margin_call_threshold: Decimal = Decimal("0.5"),
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

    def get_margin_ratio(self) -> Decimal:
        """Get current margin ratio for API compatibility.

        Returns:
            Margin usage ratio (0 for spot trading).
        """
        # For spot trading, return 0 (no margin used)
        if self.core.trading_mode == TradingMode.SPOT:
            return Decimal("0.0")

        # For futures/margin, calculate margin usage
        total_margin = self.core.used_margin()
        if total_margin == 0:
            return Decimal("0.0")
        total_margin_decimal = to_decimal(total_margin)
        initial_capital_decimal = to_decimal(self.core.initial_capital)
        return total_margin_decimal / initial_capital_decimal

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
        return float(position.size) if position else 0.0

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
        return float(position.leverage) if position else 0.0

    def get_unrealized_pnl(self, symbol: Symbol, current_price: Decimal) -> float:
        """Get unrealized PnL for a specific position.

        Args:
            symbol: Trading symbol
            current_price: Current market price

        Returns:
            Unrealized PnL (0 if no position).
        """
        from src.core.utils.validation import validate_symbol

        symbol = validate_symbol(symbol)
        # Keep current_price as Decimal for precision
        position = self.core.positions.get(symbol)
        return float(position.unrealized_pnl(current_price)) if position else 0.0
