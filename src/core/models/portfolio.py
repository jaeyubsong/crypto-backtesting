"""
Portfolio domain model.
To be implemented in Phase 2.
"""

from dataclasses import dataclass
from datetime import datetime

from src.core.constants import (
    MAX_POSITIONS_PER_PORTFOLIO,
    MAX_TRADE_SIZE,
    MAX_TRADES_HISTORY,
    MIN_TRADE_SIZE,
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

from .position import Position, Trade


@dataclass
class Portfolio(IPortfolio):
    """Portfolio domain model."""

    initial_capital: float
    cash: float
    positions: dict[Symbol, Position]
    trades: list[Trade]
    portfolio_history: list[dict]
    trading_mode: TradingMode

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
            raise PositionNotFoundError(symbol.value)

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
        # Validate inputs
        symbol = validate_symbol(symbol)
        price = validate_positive(price, "price")
        amount = validate_positive(amount, "amount")
        leverage = validate_positive(leverage, "leverage")

        # Check trade size limits
        if amount < MIN_TRADE_SIZE:
            raise ValidationError(f"Trade size too small: {amount} < {MIN_TRADE_SIZE}")
        if amount > MAX_TRADE_SIZE:
            raise ValidationError(f"Trade size too large: {amount} > {MAX_TRADE_SIZE}")

        # Calculate margin needed
        notional_value = amount * price
        margin_needed = notional_value / leverage if leverage > 0 else notional_value

        # Check if we have enough cash
        if margin_needed > self.cash:
            raise InsufficientFundsError(
                required=margin_needed,
                available=self.cash,
                operation=f"buying {amount} {symbol.value} at {price}",
            )

        # Check for existing position
        if symbol in self.positions:
            existing = self.positions[symbol]
            if existing.position_type == PositionType.SHORT:
                # Closing short position
                close_price = price
                fee = notional_value * 0.001  # 0.1% fee
                self.close_position_at_price(symbol, close_price, fee)
                # Record trade
                trade = Trade(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    action=ActionType.BUY,
                    quantity=amount,
                    price=price,
                    leverage=leverage,
                    fee=fee,
                    position_type=PositionType.SHORT,
                    pnl=existing.unrealized_pnl(price) - fee,
                    margin_used=0,
                )
                self.trades.append(trade)
            # Trim trade history if it gets too long
            if len(self.trades) > MAX_TRADES_HISTORY:
                self.trades = self.trades[-MAX_TRADES_HISTORY:]
            else:
                # Add to existing long position
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
            # Open new long position
            position = Position(
                symbol=symbol,
                size=amount,
                entry_price=price,
                leverage=leverage,
                timestamp=datetime.now(),
                position_type=PositionType.LONG,
                margin_used=margin_needed,
            )
            self.add_position(position)

            # Record trade
            trade = Trade(
                timestamp=datetime.now(),
                symbol=symbol,
                action=ActionType.BUY,
                quantity=amount,
                price=price,
                leverage=leverage,
                fee=notional_value * 0.001,  # 0.1% fee
                position_type=PositionType.LONG,
                pnl=0,
                margin_used=margin_needed,
            )
            self.trades.append(trade)
            # Trim trade history if it gets too long
            if len(self.trades) > MAX_TRADES_HISTORY:
                self.trades = self.trades[-MAX_TRADES_HISTORY:]

        return True

    def sell(self, symbol: Symbol, amount: float, price: float, leverage: float = 1.0) -> bool:
        """Execute a sell order.

        - For SPOT: Sell asset (close long position)
        - For FUTURES: Open short or close long position
        """
        # Validate inputs
        symbol = validate_symbol(symbol)
        price = validate_positive(price, "price")
        amount = validate_positive(amount, "amount")
        leverage = validate_positive(leverage, "leverage")

        # Check trade size limits
        if amount < MIN_TRADE_SIZE:
            raise ValidationError(f"Trade size too small: {amount} < {MIN_TRADE_SIZE}")
        if amount > MAX_TRADE_SIZE:
            raise ValidationError(f"Trade size too large: {amount} > {MAX_TRADE_SIZE}")

        # Calculate margin needed for short position
        notional_value = amount * price
        margin_needed = notional_value / leverage if leverage > 0 else notional_value

        # Check for existing position
        if symbol in self.positions:
            existing = self.positions[symbol]
            if existing.position_type == PositionType.LONG:
                # Closing long position
                if self.trading_mode == TradingMode.SPOT and amount > existing.size:
                    # For spot, can only sell what we have
                    return False

                close_price = price
                fee = notional_value * 0.001  # 0.1% fee

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
                    timestamp=datetime.now(),
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
            # Trim trade history if it gets too long
            if len(self.trades) > MAX_TRADES_HISTORY:
                self.trades = self.trades[-MAX_TRADES_HISTORY:]
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
                timestamp=datetime.now(),
                position_type=PositionType.SHORT,
                margin_used=margin_needed,
            )
            self.add_position(position)

            # Record trade
            trade = Trade(
                timestamp=datetime.now(),
                symbol=symbol,
                action=ActionType.SELL,
                quantity=amount,
                price=price,
                leverage=leverage,
                fee=notional_value * 0.001,  # 0.1% fee
                position_type=PositionType.SHORT,
                pnl=0,
                margin_used=margin_needed,
            )
            self.trades.append(trade)
            # Trim trade history if it gets too long
            if len(self.trades) > MAX_TRADES_HISTORY:
                self.trades = self.trades[-MAX_TRADES_HISTORY:]

        return True

    def close_position(self, symbol: Symbol, percentage: float = 100.0) -> bool:
        """Close a position (partially or fully).

        Args:
            symbol: Symbol to close
            percentage: Percentage of position to close (0-100)
        """
        # Validate inputs
        symbol = validate_symbol(symbol)
        percentage = validate_percentage(percentage)

        if symbol not in self.positions:
            return False

        position = self.positions[symbol]
        close_amount = position.size * (percentage / 100.0)

        # Estimate current price (would come from market data in real implementation)
        # For now, use entry price as placeholder
        close_price = position.entry_price
        fee = close_amount * close_price * 0.001  # 0.1% fee

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
