"""
Main Portfolio class - orchestrates all portfolio components.

This module provides the main Portfolio interface by composing the focused
components: core state, trading operations, risk management, and metrics.
"""

from collections import deque
from datetime import datetime
from decimal import Decimal
from typing import Any

from src.core.enums import Symbol, TradingMode
from src.core.interfaces.portfolio import IPortfolio
from src.core.models.position import Position, Trade
from src.core.types.financial import to_decimal

from .portfolio_core import PortfolioCore
from .portfolio_metrics import PortfolioMetrics
from .portfolio_risk import PortfolioRisk
from .portfolio_trading import PortfolioTrading


class Portfolio(IPortfolio):
    """Main Portfolio implementation.

    Orchestrates portfolio operations by composing focused components:
    - PortfolioCore: State management
    - PortfolioTrading: Buy/sell operations
    - PortfolioRisk: Liquidation and risk management
    - PortfolioMetrics: Calculations and metrics

    This design follows the Single Responsibility Principle and Composition pattern.
    """

    def __init__(
        self,
        initial_capital: float | Decimal,
        cash: float | Decimal,
        positions: dict[Symbol, Position] | None = None,
        trades: deque[Trade] | None = None,
        portfolio_history: deque[dict[str, Any]] | None = None,
        trading_mode: TradingMode = TradingMode.SPOT,
    ) -> None:
        """Initialize Portfolio with composition pattern."""
        # Initialize collections if not provided
        if positions is None:
            positions = {}
        if trades is None:
            trades = deque()
        if portfolio_history is None:
            portfolio_history = deque()

        # Convert float inputs to Decimal for internal use
        initial_capital_decimal = to_decimal(initial_capital)
        cash_decimal = to_decimal(cash)

        # Create the core state manager first - single source of truth
        self._core = PortfolioCore(
            initial_capital=initial_capital_decimal,
            cash=cash_decimal,
            positions=positions,
            trades=trades,
            portfolio_history=portfolio_history,
            trading_mode=trading_mode,
        )

        # Store reference values for interface compatibility
        self.initial_capital = initial_capital_decimal
        self.trading_mode = trading_mode

        # Initialize specialized components
        self._trading = PortfolioTrading(self._core)
        self._risk = PortfolioRisk(self._core)
        self._metrics = PortfolioMetrics(self._core)

    # Simplified property delegation - core is always available
    @property
    def cash(self) -> float:
        """Get current cash (delegates to core)."""
        return float(self._core.cash)

    @cash.setter
    def cash(self, value: float) -> None:
        """Set cash value (delegates to core)."""
        self._core.cash = to_decimal(value)

    @property
    def positions(self) -> dict[Symbol, Position]:
        """Get current positions (delegates to core)."""
        return self._core.positions

    @positions.setter
    def positions(self, value: dict[Symbol, Position]) -> None:
        """Set positions (delegates to core)."""
        self._core.positions = value

    @property
    def trades(self) -> deque[Trade]:
        """Get trade history (delegates to core)."""
        return self._core.trades

    @trades.setter
    def trades(self, value: deque[Trade]) -> None:
        """Set trade history (delegates to core)."""
        self._core.trades = value

    @property
    def portfolio_history(self) -> deque[dict[str, Any]]:
        """Get portfolio history (delegates to core)."""
        return self._core.portfolio_history

    @portfolio_history.setter
    def portfolio_history(self, value: deque[dict[str, Any]]) -> None:
        """Set portfolio history (delegates to core)."""
        self._core.portfolio_history = value

    # Core Portfolio Interface (IPortfolio)
    def buy(self, symbol: Symbol, amount: float, price: float, leverage: float = 1.0) -> bool:
        """Execute a buy order."""
        return self._trading.buy(symbol, amount, price, leverage)

    def sell(self, symbol: Symbol, amount: float, price: float, leverage: float = 1.0) -> bool:
        """Execute a sell order."""
        return self._trading.sell(symbol, amount, price, leverage)

    def close_position(
        self, symbol: Symbol, current_price: float, percentage: float = 100.0
    ) -> bool:
        """Close a position."""
        return self._risk.close_position(symbol, to_decimal(current_price), to_decimal(percentage))

    def calculate_portfolio_value(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate total portfolio value."""
        # Convert float prices to Decimal for internal calculations
        decimal_prices = {symbol: to_decimal(price) for symbol, price in current_prices.items()}
        result = self._metrics.calculate_portfolio_value(decimal_prices)
        return float(result)

    def available_margin(self) -> float:
        """Get available margin."""
        return float(self._core.available_margin())

    def used_margin(self) -> float:
        """Get used margin."""
        return float(self._core.used_margin())

    def margin_ratio(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate margin ratio."""
        # Convert float prices to Decimal for internal calculations
        decimal_prices = {symbol: to_decimal(price) for symbol, price in current_prices.items()}
        result = self._metrics.margin_ratio(decimal_prices)
        return float(result)

    def check_liquidation(
        self, current_prices: dict[Symbol, float], maintenance_margin_rate: float = 0.05
    ) -> list[Symbol]:
        """Check and return symbols at risk of liquidation."""
        # Convert float prices to Decimal for internal calculations
        decimal_prices = {symbol: to_decimal(price) for symbol, price in current_prices.items()}
        return self._risk.check_liquidation(decimal_prices, to_decimal(maintenance_margin_rate))

    # Strategy API Methods (PRD Section 3.2)
    def get_position_size(self, symbol: Symbol) -> float:
        """Get current position size for symbol."""
        return self._metrics.get_position_size(symbol)

    def get_cash(self) -> float:
        """Get available cash/margin."""
        return float(self._core.cash)

    def get_margin_ratio(self) -> float:
        """Get current margin ratio."""
        result = self._metrics.get_margin_ratio()
        return float(result)

    def get_unrealized_pnl(self, symbol: Symbol, current_price: float) -> float:
        """Get unrealized PnL for a specific position."""
        from src.core.utils.validation import validate_positive
        validate_positive(current_price, "current_price")
        return self._metrics.get_unrealized_pnl(symbol, to_decimal(current_price))

    def get_leverage(self, symbol: Symbol) -> float:
        """Get current leverage for a position."""
        return self._metrics.get_leverage(symbol)

    def record_snapshot(self, timestamp: datetime, current_prices: dict[Symbol, float]) -> None:
        """Record portfolio state at given timestamp."""
        # Convert float prices to Decimal for internal storage
        decimal_prices = {symbol: to_decimal(price) for symbol, price in current_prices.items()}
        self._core.record_snapshot(timestamp, decimal_prices)

    # Additional utility methods
    def realized_pnl(self) -> float:
        """Calculate total realized PnL from completed trades."""
        result = self._core.realized_pnl()
        return float(result)

    def unrealized_pnl(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate total unrealized PnL from all positions."""
        # Convert float prices to Decimal for internal calculations
        decimal_prices = {symbol: to_decimal(price) for symbol, price in current_prices.items()}
        result = self._core.unrealized_pnl(decimal_prices)
        return float(result)

    def is_margin_call(
        self, current_prices: dict[Symbol, float], margin_call_threshold: float = 0.5
    ) -> bool:
        """Check if portfolio is at risk of margin call."""
        # Convert float prices to Decimal for internal calculations
        decimal_prices = {symbol: to_decimal(price) for symbol, price in current_prices.items()}
        return self._metrics.is_margin_call(decimal_prices, to_decimal(margin_call_threshold))

    # Additional methods needed by tests and external code
    def add_position(self, position: Position) -> None:
        """Add a new position to the portfolio."""
        self._core.add_position(position)

    def close_position_at_price(self, symbol: Symbol, close_price: float, fee: float) -> float:
        """Close a position at a specific price and return realized PnL."""
        result = self._risk.close_position_at_price(
            symbol, to_decimal(close_price), to_decimal(fee)
        )
        return float(result)
