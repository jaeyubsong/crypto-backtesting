"""
Portfolio domain model.
To be implemented in Phase 2.
"""

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.core.constants import (
    DEFAULT_TAKER_FEE,
    MAX_POSITIONS_PER_PORTFOLIO,
)
from src.core.enums import ActionType, PositionType, Symbol, TradingMode
from src.core.exceptions.backtest import (
    InsufficientFundsError,
    PositionNotFoundError,
    ValidationError,
)
from src.core.interfaces.portfolio import IPortfolio
from src.core.utils.validation import (
    validate_percentage,
    validate_positive,
    validate_symbol,
)

from .portfolio_helpers import (
    FeeCalculator,
    OrderValidator,
    PositionManager,
    TradeRecorder,
)
from .position import Position, Trade


@dataclass
class Portfolio(IPortfolio):
    """Portfolio domain model."""

    initial_capital: float
    cash: float
    positions: dict[Symbol, Position]
    trades: deque[Trade]
    portfolio_history: deque[dict]
    trading_mode: TradingMode
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def calculate_portfolio_value(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate total portfolio value based on trading mode.

        - FUTURES: Portfolio Value = Equity = Cash + Unrealized PnL
        - SPOT/MARGIN: Portfolio Value = Cash + Asset Values
        """
        if self.trading_mode == TradingMode.FUTURES:
            # For futures: equity = cash + unrealized PnL
            return self.cash + self.unrealized_pnl(current_prices)
        else:
            # For spot/margin: add actual position values
            total_value = self.cash
            for symbol, position in self.positions.items():
                if symbol in current_prices:
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
        # Check position limit
        if len(self.positions) >= MAX_POSITIONS_PER_PORTFOLIO:
            raise ValidationError(
                f"Maximum positions limit reached ({MAX_POSITIONS_PER_PORTFOLIO})"
            )

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

    def close_position_at_price(self, symbol: Symbol, close_price: float, fee: float) -> float:
        """Close a position at a specific price and return realized PnL.

        This is the original method for closing with known price.
        """
        # Validate inputs
        if not symbol or not isinstance(symbol, Symbol):
            raise ValidationError("Symbol must be a valid Symbol enum")
        if close_price <= 0:
            raise ValidationError("Close price must be positive")
        if fee < 0:
            raise ValidationError("Fee must be non-negative")

        if symbol not in self.positions:
            raise PositionNotFoundError(str(symbol))

        position = self.positions[symbol]
        unrealized_pnl = position.unrealized_pnl(close_price)
        realized_pnl = unrealized_pnl - fee

        # Release margin and add realized PnL
        self.cash += position.margin_used + realized_pnl

        # Remove position
        del self.positions[symbol]

        return realized_pnl

    def buy(self, symbol: Symbol, amount: float, price: float, leverage: float = 1.0) -> bool:
        """Execute a buy order.

        - For SPOT: Buy asset (open long position)
        - For FUTURES: Open long or close short position
        """
        # Validate and calculate
        symbol, amount, price, leverage = OrderValidator.validate_order(
            symbol, amount, price, leverage
        )
        notional_value, margin_needed = OrderValidator.calculate_margin_needed(
            amount, price, leverage
        )

        with self._lock:  # Thread-safe operation
            OrderValidator.check_sufficient_funds(
                margin_needed, self.cash, f"buying {amount} {symbol.value} at {price}"
            )

            # Check for existing position
            if symbol in self.positions:
                existing = self.positions[symbol]
                if existing.position_type == PositionType.SHORT:
                    # Closing short position
                    self._close_short_position(
                        symbol, existing, amount, price, leverage, notional_value
                    )
                else:
                    # Add to existing long position
                    self._add_to_long_position(existing, amount, price, margin_needed)
            else:
                # Open new long position
                self._open_long_position(
                    symbol, amount, price, leverage, notional_value, margin_needed
                )

            return True

    def sell(self, symbol: Symbol, amount: float, price: float, leverage: float = 1.0) -> bool:
        """Execute a sell order.

        - For SPOT: Sell asset (close long position)
        - For FUTURES: Open short or close long position
        """
        # Validate and calculate
        symbol, amount, price, leverage = OrderValidator.validate_order(
            symbol, amount, price, leverage
        )
        notional_value, margin_needed = OrderValidator.calculate_margin_needed(
            amount, price, leverage
        )

        with self._lock:  # Thread-safe operation
            # Check for existing position
            if symbol in self.positions:
                existing = self.positions[symbol]
                if existing.position_type == PositionType.LONG:
                    # Closing long position
                    if self.trading_mode == TradingMode.SPOT and amount > existing.size:
                        # For spot, can only sell what we have
                        return False

                    close_price = price
                    fee = notional_value * DEFAULT_TAKER_FEE

                    if amount >= existing.size:
                        # Close entire position
                        self.close_position_at_price(symbol, close_price, fee)
                    else:
                        # Partial close
                        partial_pnl = (close_price - existing.entry_price) * amount - fee
                        partial_margin = existing.margin_used * (amount / existing.size)

                        existing.size -= amount
                        existing.margin_used -= partial_margin
                        self.cash += partial_margin + partial_pnl

                    # Record trade
                    trade = Trade(
                        timestamp=datetime.now(UTC),
                        symbol=symbol,
                        action=ActionType.SELL,
                        quantity=amount,
                        price=price,
                        leverage=leverage,
                        fee=fee,
                        position_type=PositionType.LONG,
                        pnl=existing.unrealized_pnl(price) * (amount / existing.size) - fee,
                        margin_used=0,
                    )
                    self.trades.append(trade)
                else:
                    # Add to existing short position (futures only)
                    if self.trading_mode == TradingMode.SPOT:
                        return False  # Can't short in spot trading

                    if margin_needed > self.cash:
                        raise InsufficientFundsError(
                            required=margin_needed,
                            available=self.cash,
                            operation=f"adding to short position {symbol.value}",
                        )

                    # Calculate new average entry price
                    total_size = existing.size + amount
                    total_value = (existing.size * existing.entry_price) + (amount * price)
                    new_entry_price = total_value / total_size

                    # Update position
                    existing.size = total_size
                    existing.entry_price = new_entry_price
                    existing.margin_used += margin_needed
                    self.cash -= margin_needed
            else:
                # Open new short position (futures only)
                if self.trading_mode == TradingMode.SPOT:
                    return False  # Can't open short in spot

                if margin_needed > self.cash:
                    raise InsufficientFundsError(
                        required=margin_needed,
                        available=self.cash,
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
                self.add_position(position)

                # Record trade
                trade = Trade(
                    timestamp=datetime.now(UTC),
                    symbol=symbol,
                    action=ActionType.SELL,
                    quantity=amount,
                    price=price,
                    leverage=leverage,
                    fee=notional_value * DEFAULT_TAKER_FEE,
                    position_type=PositionType.SHORT,
                    pnl=0,
                    margin_used=margin_needed,
                )
                self.trades.append(trade)

            return True

    def close_position(
        self, symbol: Symbol, current_price: float, percentage: float = 100.0
    ) -> bool:
        """Close a position (partially or fully).

        Args:
            symbol: Symbol to close
            current_price: Current market price for closing
            percentage: Percentage of position to close (0-100)
        """
        # Validate inputs
        symbol = validate_symbol(symbol)
        current_price = validate_positive(current_price, "current_price")
        percentage = validate_percentage(percentage)

        if symbol not in self.positions:
            return False

        position = self.positions[symbol]
        close_amount = position.size * (percentage / 100.0)

        close_price = current_price
        fee = close_amount * close_price * DEFAULT_TAKER_FEE

        if percentage >= 100:
            # Full close
            self.close_position_at_price(symbol, close_price, fee)
        else:
            # Partial close
            partial_pnl = position.unrealized_pnl(close_price) * (percentage / 100.0) - fee
            partial_margin = position.margin_used * (percentage / 100.0)

            position.size *= 1 - percentage / 100.0
            position.margin_used *= 1 - percentage / 100.0
            self.cash += partial_margin + partial_pnl

        return True

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

        for symbol, position in self.positions.items():
            if symbol not in current_prices:
                continue

            # Check if position is at liquidation risk
            if position.is_liquidation_risk(current_prices[symbol], maintenance_margin_rate):
                at_risk_symbols.append(symbol)

        return at_risk_symbols

    # Strategy API Methods (PRD Section 3.2)
    def get_position_size(self, symbol: Symbol) -> float:
        """Get current position size for symbol.

        Returns:
            Positive for long, negative for short, 0 if no position.
        """
        symbol = validate_symbol(symbol)
        position = self.positions.get(symbol)
        return position.size if position else 0.0

    def get_cash(self) -> float:
        """Get available cash/margin.

        Returns:
            Current cash balance.
        """
        return self.cash

    def get_margin_ratio(self) -> float:
        """Get current margin ratio.

        Returns:
            Margin usage ratio (0 for spot trading).
        """
        # For spot trading, return 0 (no margin used)
        if self.trading_mode == TradingMode.SPOT:
            return 0.0

        # For futures/margin, calculate margin usage
        total_margin = self.used_margin()
        if total_margin == 0:
            return 0.0
        return total_margin / self.initial_capital

    def get_unrealized_pnl(self, symbol: Symbol, current_price: float) -> float:
        """Get unrealized PnL for a specific position.

        Args:
            symbol: Trading symbol
            current_price: Current market price

        Returns:
            Unrealized PnL (0 if no position).
        """
        symbol = validate_symbol(symbol)
        current_price = validate_positive(current_price, "current_price")

        position = self.positions.get(symbol)
        return position.unrealized_pnl(current_price) if position else 0.0

    def get_leverage(self, symbol: Symbol) -> float:
        """Get current leverage for a position.

        Args:
            symbol: Trading symbol

        Returns:
            Position leverage (0 if no position).
        """
        symbol = validate_symbol(symbol)
        position = self.positions.get(symbol)
        return position.leverage if position else 0.0

    def record_snapshot(self, timestamp: datetime, current_prices: dict[Symbol, float]) -> None:
        """Record portfolio state at given timestamp.

        Args:
            timestamp: Current timestamp
            current_prices: Current market prices for all symbols
        """
        snapshot = {
            "timestamp": timestamp,
            "portfolio_value": self.calculate_portfolio_value(current_prices),
            "cash": self.cash,
            "unrealized_pnl": self.unrealized_pnl(current_prices),
            "realized_pnl": self.realized_pnl(),
            "margin_used": self.used_margin(),
            "positions": len(self.positions),
            "leverage_ratio": self.get_margin_ratio(),
        }

        self.portfolio_history.append(snapshot)

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
        fee = FeeCalculator.calculate_fee(notional_value)
        self.close_position_at_price(symbol, price, fee)

        trade = TradeRecorder.create_trade(
            symbol=symbol,
            action=ActionType.BUY,
            quantity=amount,
            price=price,
            leverage=leverage,
            fee=fee,
            position_type=PositionType.SHORT,
            pnl=position.unrealized_pnl(price) - fee,
            margin_used=0,
        )
        self.trades.append(trade)

    def _add_to_long_position(
        self, position: Position, amount: float, price: float, margin_needed: float
    ) -> None:
        """Add to existing long position."""
        PositionManager.update_position_size(position, amount, price, margin_needed)
        self.cash -= margin_needed

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
            margin_used=margin_needed,
        )
        self.add_position(position)

        fee = FeeCalculator.calculate_fee(notional_value)
        trade = TradeRecorder.create_trade(
            symbol=symbol,
            action=ActionType.BUY,
            quantity=amount,
            price=price,
            leverage=leverage,
            fee=fee,
            position_type=PositionType.LONG,
            pnl=0,
            margin_used=margin_needed,
        )
        self.trades.append(trade)
