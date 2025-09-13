"""
Main Portfolio class - orchestrates all portfolio components.

This module provides the main Portfolio interface by composing the focused
components: core state, trading operations, risk management, and metrics.
"""

from collections import deque
from datetime import datetime
from typing import Any

from src.core.enums import Symbol, TradingMode
from src.core.interfaces.portfolio import IPortfolio
from src.core.models.position import Position, Trade

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
        initial_capital: float,
        cash: float,
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

        # Create the core state manager first - single source of truth
        self._core = PortfolioCore(
            initial_capital=initial_capital,
            cash=cash,
            positions=positions,
            trades=trades,
            portfolio_history=portfolio_history,
            trading_mode=trading_mode,
        )

        # Store reference values for interface compatibility
        self.initial_capital = initial_capital
        self.trading_mode = trading_mode

        # Initialize specialized components
        self._trading = PortfolioTrading(self._core)
        self._risk = PortfolioRisk(self._core)
        self._metrics = PortfolioMetrics(self._core)

    # Simplified property delegation - core is always available
    @property
    def cash(self) -> float:
        """Get current cash (delegates to core)."""
        return self._core.cash

    @cash.setter
    def cash(self, value: float) -> None:
        """Set cash value (delegates to core)."""
        self._core.cash = value

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
        return self._risk.close_position(symbol, current_price, percentage)

    def calculate_portfolio_value(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate total portfolio value."""
        return self._metrics.calculate_portfolio_value(current_prices)

    def available_margin(self) -> float:
        """Get available margin."""
        return self._core.available_margin()

    def used_margin(self) -> float:
        """Get used margin."""
        return self._core.used_margin()

    def margin_ratio(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate margin ratio."""
        return self._metrics.margin_ratio(current_prices)

    def check_liquidation(
        self, current_prices: dict[Symbol, float], maintenance_margin_rate: float = 0.05
    ) -> list[Symbol]:
        """Check and return symbols at risk of liquidation."""
        return self._risk.check_liquidation(current_prices, maintenance_margin_rate)

    # Strategy API Methods (PRD Section 3.2)
    def get_position_size(self, symbol: Symbol) -> float:
        """Get current position size for symbol."""
        return self._metrics.get_position_size(symbol)

    def get_cash(self) -> float:
        """Get available cash/margin."""
        return self._core.cash

    def get_margin_ratio(self) -> float:
        """Get current margin ratio."""
        return self._metrics.get_margin_ratio()

    def get_unrealized_pnl(self, symbol: Symbol, current_price: float) -> float:
        """Get unrealized PnL for a specific position."""
        return self._metrics.get_unrealized_pnl(symbol, current_price)

    def get_leverage(self, symbol: Symbol) -> float:
        """Get current leverage for a position."""
        return self._metrics.get_leverage(symbol)

    def record_snapshot(self, timestamp: datetime, current_prices: dict[Symbol, float]) -> None:
        """Record portfolio state at given timestamp."""
        self._core.record_snapshot(timestamp, current_prices)

    # Additional utility methods
    def realized_pnl(self) -> float:
        """Calculate total realized PnL from completed trades."""
        return self._core.realized_pnl()

    def unrealized_pnl(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate total unrealized PnL from all positions."""
        return self._core.unrealized_pnl(current_prices)

    def is_margin_call(
        self, current_prices: dict[Symbol, float], margin_call_threshold: float = 0.5
    ) -> bool:
        """Check if portfolio is at risk of margin call."""
        return self._metrics.is_margin_call(current_prices, margin_call_threshold)

    # Additional methods needed by tests and external code
    def add_position(self, position: Position) -> None:
        """Add a new position to the portfolio."""
        self._core.add_position(position)

    def close_position_at_price(self, symbol: Symbol, close_price: float, fee: float) -> float:
        """Close a position at a specific price and return realized PnL."""
        return self._risk.close_position_at_price(symbol, close_price, fee)
