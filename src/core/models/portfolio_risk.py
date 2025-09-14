"""
Portfolio risk management.

This module handles liquidation detection, margin calls, and risk controls
following the Single Responsibility Principle for risk management.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from src.core.constants import DEFAULT_TAKER_FEE
from src.core.enums import Symbol
from src.core.exceptions.backtest import PositionNotFoundError
from src.core.types.financial import to_decimal, AmountFloat, PriceFloat
from src.core.utils.validation import validate_positive, validate_symbol

from .portfolio_helpers import PortfolioValidator

if TYPE_CHECKING:
    from .portfolio_core import PortfolioCore


class PortfolioRisk:
    """Portfolio risk management.

    Handles liquidation detection, position closure, and risk controls.
    """

    def __init__(self, portfolio_core: "PortfolioCore") -> None:
        """Initialize with portfolio core state.

        Args:
            portfolio_core: The portfolio core state to manage risks for
        """
        self.core = portfolio_core

    def check_liquidation(
        self, current_prices: dict[Symbol, float], maintenance_margin_rate: float = 0.05
    ) -> list[Symbol]:
        """Check and return symbols at risk of liquidation.

        Args:
            current_prices: Current market prices
            maintenance_margin_rate: Maintenance margin requirement (default 5%)

        Returns:
            List of symbols that should be liquidated
        """
        at_risk_symbols = []

        for symbol, position in self.core.positions.items():
            if symbol not in current_prices:
                continue

            # Check if position is at liquidation risk
            if position.is_liquidation_risk(current_prices[symbol], maintenance_margin_rate):
                at_risk_symbols.append(symbol)

        return at_risk_symbols

    def close_position_at_price(self, symbol: Symbol, close_price: PriceFloat, fee: AmountFloat) -> Decimal:
        """Close a position at a specific price and return realized PnL.

        This is the original method for closing with known price.

        Args:
            symbol: Symbol to close
            close_price: Price at which to close
            fee: Trading fee to deduct

        Returns:
            Realized PnL from closing the position

        Raises:
            ValidationError: If parameters are invalid
            PositionNotFoundError: If position doesn't exist
        """
        # Use centralized validator for parameter validation
        symbol, close_price, fee = PortfolioValidator.validate_close_position_params(
            symbol, close_price, fee
        )

        if symbol not in self.core.positions:
            raise PositionNotFoundError(str(symbol))

        position = self.core.positions[symbol]
        unrealized_pnl = position.unrealized_pnl(close_price)
        realized_pnl = unrealized_pnl - to_decimal(fee)

        # Release margin and add realized PnL
        self.core.cash += position.margin_used + realized_pnl

        # Remove position
        del self.core.positions[symbol]

        return realized_pnl

    def close_position(
        self, symbol: Symbol, current_price: PriceFloat, percentage: AmountFloat = 100.0
    ) -> bool:
        """Close a position (partially or fully).

        Args:
            symbol: Symbol to close
            current_price: Current market price for closing
            percentage: Percentage of position to close (0-100)

        Returns:
            True if position was closed successfully
        """
        # Validate inputs using centralized validator
        symbol = validate_symbol(symbol)
        current_price = validate_positive(current_price, "current_price")
        percentage = PortfolioValidator.validate_percentage(percentage, "position close percentage")

        if symbol not in self.core.positions:
            return False

        position = self.core.positions[symbol]
        close_amount = position.size * (to_decimal(percentage) / to_decimal(100.0))

        close_price = to_decimal(current_price)
        fee = close_amount * close_price * to_decimal(DEFAULT_TAKER_FEE)

        if percentage >= 100:
            # Full close
            self.close_position_at_price(symbol, close_price, fee)
        else:
            # Partial close
            percentage_decimal = to_decimal(percentage) / to_decimal(100.0)
            partial_pnl = position.unrealized_pnl(close_price) * percentage_decimal - fee
            partial_margin = position.margin_used * percentage_decimal

            remaining_percentage = to_decimal(1) - percentage_decimal
            position.size *= remaining_percentage
            position.margin_used *= remaining_percentage
            self.core.cash += partial_margin + partial_pnl

        return True
