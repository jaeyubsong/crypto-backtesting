"""
Portfolio trading operations.

This module handles buy/sell operations and trade execution
following the Single Responsibility Principle for trading logic.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.core.constants import DEFAULT_TAKER_FEE, MIN_TRADE_SIZE
from src.core.enums import ActionType, PositionType, Symbol, TradingMode
from src.core.exceptions.backtest import InsufficientFundsError, ValidationError
from src.core.models.position import Position
from src.core.models.trade import Trade

from .portfolio_helpers import (
    FeeCalculator,
    OrderValidator,
    PositionManager,
    TradeRecorder,
)

if TYPE_CHECKING:
    from .portfolio_core import PortfolioCore


class PortfolioTrading:
    """Portfolio trading operations.

    Handles buy/sell operations, trade execution, and position management.
    """

    def __init__(self, portfolio_core: "PortfolioCore") -> None:
        """Initialize with portfolio core state.

        Args:
            portfolio_core: The portfolio core state to execute trades for
        """
        self.core = portfolio_core

    def _handle_existing_position_buy(
        self,
        symbol: Symbol,
        existing: Position,
        amount: float,
        price: float,
        leverage: float,
        notional_value: float,
        margin_needed: float,
    ) -> None:
        """Handle buy order when position already exists."""
        if existing.position_type == PositionType.SHORT:
            self._close_short_position(symbol, existing, amount, price, leverage, notional_value)
        else:
            self._add_to_long_position(existing, amount, price, margin_needed)

    def buy(self, symbol: Symbol, amount: float, price: float, leverage: float = 1.0) -> bool:
        """Execute a buy order.

        - For SPOT: Buy asset (open long position)
        - For FUTURES: Open long or close short position

        Args:
            symbol: Trading symbol
            amount: Amount to buy
            price: Price per unit
            leverage: Leverage to use (default 1.0)

        Returns:
            True if order executed successfully
        """
        symbol, amount, price, leverage = OrderValidator.validate_order(
            symbol, amount, price, leverage
        )
        notional_value, margin_needed = OrderValidator.calculate_margin_needed(
            amount, price, leverage
        )

        with self.core._lock:
            OrderValidator.check_sufficient_funds(
                margin_needed, self.core.cash, f"buying {amount} {symbol.value} at {price}"
            )

            if symbol in self.core.positions:
                self._handle_existing_position_buy(
                    symbol,
                    self.core.positions[symbol],
                    amount,
                    price,
                    leverage,
                    notional_value,
                    margin_needed,
                )
            else:
                self._open_long_position(
                    symbol, amount, price, leverage, notional_value, margin_needed
                )

            return True

    def sell(self, symbol: Symbol, amount: float, price: float, leverage: float = 1.0) -> bool:
        """Execute a sell order.

        - For SPOT: Sell asset (close long position)
        - For FUTURES: Open short or close long position

        Args:
            symbol: Trading symbol
            amount: Amount to sell
            price: Price per unit
            leverage: Leverage to use (default 1.0)

        Returns:
            True if order executed successfully
        """
        symbol, amount, price, leverage = OrderValidator.validate_order(
            symbol, amount, price, leverage
        )
        notional_value, margin_needed = OrderValidator.calculate_margin_needed(
            amount, price, leverage
        )

        with self.core._lock:
            if symbol in self.core.positions:
                return self._handle_existing_position_sell(
                    symbol, amount, price, leverage, notional_value, margin_needed
                )
            else:
                return self._open_new_short_position(
                    symbol, amount, price, leverage, notional_value, margin_needed
                )

    def _handle_existing_position_sell(
        self,
        symbol: Symbol,
        amount: float,
        price: float,
        _leverage: float,
        notional_value: float,
        margin_needed: float,
    ) -> bool:
        """Handle sell order when position already exists."""
        existing = self.core.positions[symbol]
        if existing.position_type == PositionType.LONG:
            self._close_long_position(symbol, existing, amount, price, notional_value)
        else:
            self._add_to_short_position(existing, amount, price, margin_needed, symbol)
        return True

    def _add_to_short_position(
        self, existing: Position, amount: float, price: float, margin_needed: float, symbol: Symbol
    ) -> None:
        """Add to existing short position (futures only)."""
        if self.core.trading_mode == TradingMode.SPOT:
            return  # Can't short in spot trading

        if margin_needed > self.core.cash:
            raise InsufficientFundsError(
                required=float(margin_needed),
                available=float(self.core.cash),
                operation=f"adding to short position {symbol.value}",
            )

        total_size = existing.size + amount
        total_value = (existing.size * existing.entry_price) + (amount * price)

        if abs(total_size) < MIN_TRADE_SIZE:
            raise ValidationError(f"Invalid position averaging: total size {total_size} too small")

        existing.size = total_size
        existing.entry_price = total_value / total_size
        existing.margin_used += margin_needed
        self.core.cash -= margin_needed

    def _open_new_short_position(
        self,
        symbol: Symbol,
        amount: float,
        price: float,
        leverage: float,
        notional_value: float,
        margin_needed: float,
    ) -> bool:
        """Open new short position (futures only)."""
        if self.core.trading_mode == TradingMode.SPOT:
            return False  # Can't open short in spot

        if margin_needed > self.core.cash:
            raise InsufficientFundsError(
                required=float(margin_needed),
                available=float(self.core.cash),
                operation=f"opening short position {symbol.value}",
            )

        position = Position(
            symbol=symbol,
            size=amount,
            entry_price=price,
            leverage=leverage,
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=margin_needed,
        )
        self.core.add_position(position)

        trade = Trade(
            timestamp=datetime.now(UTC),
            symbol=symbol,
            action=ActionType.SELL,
            quantity=amount,
            price=price,
            leverage=leverage,
            fee=float(notional_value * DEFAULT_TAKER_FEE),
            position_type=PositionType.SHORT,
            pnl=0,
            margin_used=float(margin_needed),
        )
        self.core.trades.append(trade)
        return True

    # Helper methods to reduce complexity
    def _close_short_position(
        self,
        symbol: Symbol,
        position: Position,
        amount: float,
        price: float,
        leverage: float,
        notional_value: float,
    ) -> None:
        """Close a short position and record trade."""
        from .portfolio_risk import PortfolioRisk

        risk_manager = PortfolioRisk(self.core)
        fee = FeeCalculator.calculate_fee(notional_value)
        risk_manager.close_position_at_price(symbol, price, fee)

        trade = TradeRecorder.create_trade(
            symbol=symbol,
            action=ActionType.BUY,
            quantity=amount,
            price=price,
            leverage=leverage,
            fee=float(fee),
            position_type=PositionType.SHORT,
            pnl=float(position.unrealized_pnl(price) - fee),
            margin_used=0,
        )
        self.core.trades.append(trade)

    def _add_to_long_position(
        self, position: Position, amount: float, price: float, margin_needed: float
    ) -> None:
        """Add to existing long position."""
        PositionManager.update_position_size(position, amount, price, margin_needed)
        self.core.cash -= margin_needed

    def _open_long_position(
        self,
        symbol: Symbol,
        amount: float,
        price: float,
        leverage: float,
        notional_value: float,
        margin_needed: float,
    ) -> None:
        """Open new long position and record trade."""
        position = PositionManager.create_position(
            symbol=symbol,
            size=amount,
            entry_price=price,
            leverage=leverage,
            position_type=PositionType.LONG,
            margin_used=float(margin_needed),
        )
        self.core.add_position(position)

        fee = FeeCalculator.calculate_fee(notional_value)
        trade = TradeRecorder.create_trade(
            symbol=symbol,
            action=ActionType.BUY,
            quantity=amount,
            price=price,
            leverage=leverage,
            fee=float(fee),
            position_type=PositionType.LONG,
            pnl=0,
            margin_used=float(margin_needed),
        )
        self.core.trades.append(trade)

    def _handle_partial_position_close(
        self, position: Position, amount: float, close_price: float, fee: float
    ) -> None:
        """Handle partial closure of a position."""
        partial_pnl = (close_price - position.entry_price) * amount - fee
        partial_margin = position.margin_used * (amount / position.size)

        position.size -= amount
        position.margin_used -= partial_margin
        self.core.cash += partial_margin + partial_pnl

    def _record_position_close_trade(
        self, symbol: Symbol, amount: float, price: float, position: Position, fee: float
    ) -> None:
        """Record trade for position closure."""
        trade = Trade(
            timestamp=datetime.now(UTC),
            symbol=symbol,
            action=ActionType.SELL,
            quantity=amount,
            price=price,
            leverage=float(position.leverage),
            fee=float(fee),
            position_type=PositionType.LONG,
            pnl=float(position.unrealized_pnl(price) * (amount / position.size) - fee),
            margin_used=0,
        )
        self.core.trades.append(trade)

    def _close_long_position(
        self, symbol: Symbol, position: Position, amount: float, price: float, notional_value: float
    ) -> None:
        """Close a long position (partial or full)."""
        if self.core.trading_mode == TradingMode.SPOT and amount > position.size:
            return  # For spot, can only sell what we have

        from .portfolio_risk import PortfolioRisk

        fee = notional_value * DEFAULT_TAKER_FEE
        risk_manager = PortfolioRisk(self.core)

        if amount >= position.size:
            risk_manager.close_position_at_price(symbol, price, fee)
        else:
            self._handle_partial_position_close(position, amount, price, fee)

        self._record_position_close_trade(symbol, amount, price, position, fee)
