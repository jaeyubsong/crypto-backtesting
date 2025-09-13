"""
Portfolio core state management.

This module handles the fundamental portfolio state and basic operations,
following the Single Responsibility Principle for state management.
"""

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.core.constants import (
    MAX_PORTFOLIO_HISTORY,
    MAX_POSITIONS_PER_PORTFOLIO,
    PORTFOLIO_HISTORY_TRIM_TO,
)
from src.core.enums import Symbol, TradingMode
from src.core.exceptions.backtest import InsufficientFundsError, ValidationError
from src.core.models.position import Position, Trade


@dataclass
class PortfolioCore:
    """Core portfolio state management.

    Handles the fundamental state of a portfolio including capital,
    positions, trade history, and portfolio snapshots.
    """

    initial_capital: float
    cash: float
    positions: dict[Symbol, Position]
    trades: deque[Trade]
    portfolio_history: deque[dict[str, Any]]
    trading_mode: TradingMode
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def available_margin(self) -> float:
        """Calculate available margin for new positions."""
        return self.cash

    def used_margin(self) -> float:
        """Calculate total margin used by open positions."""
        return sum(position.margin_used for position in self.positions.values())

    def realized_pnl(self) -> float:
        """Calculate total realized PnL from completed trades."""
        return sum(trade.pnl for trade in self.trades)

    def unrealized_pnl(self, current_prices: dict[Symbol, float]) -> float:
        """Calculate total unrealized PnL from all positions."""
        total_pnl = 0.0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                total_pnl += position.unrealized_pnl(current_prices[symbol])
        return total_pnl

    def add_position(self, position: Position) -> None:
        """Add a new position to the portfolio.

        Args:
            position: Position to add

        Raises:
            ValidationError: If position limit exceeded or invalid position
        """
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

    def remove_position(self, symbol: Symbol) -> Position:
        """Remove and return a position from the portfolio.

        Args:
            symbol: Symbol of position to remove

        Returns:
            The removed position

        Raises:
            ValidationError: If position not found
        """
        if symbol not in self.positions:
            raise ValidationError(f"Position not found for symbol: {symbol}")

        return self.positions.pop(symbol)

    def record_snapshot(self, timestamp: datetime, current_prices: dict[Symbol, float]) -> None:
        """Record portfolio state at given timestamp.

        Args:
            timestamp: Current timestamp
            current_prices: Current market prices for all symbols
        """
        from .portfolio_metrics import PortfolioMetrics

        # Create metrics calculator for this snapshot
        metrics = PortfolioMetrics(self)

        snapshot = {
            "timestamp": timestamp,
            "portfolio_value": metrics.calculate_portfolio_value(current_prices),
            "cash": self.cash,
            "unrealized_pnl": self.unrealized_pnl(current_prices),
            "realized_pnl": self.realized_pnl(),
            "margin_used": self.used_margin(),
            "positions": len(self.positions),
            "leverage_ratio": metrics.get_margin_ratio(),
        }

        self.portfolio_history.append(snapshot)

        # Trim history if it exceeds the maximum limit
        if len(self.portfolio_history) > MAX_PORTFOLIO_HISTORY:
            # Keep only the most recent PORTFOLIO_HISTORY_TRIM_TO entries + 1 new entry
            entries_to_keep = PORTFOLIO_HISTORY_TRIM_TO + 1
            if hasattr(self.portfolio_history, "popleft"):
                # For deque, remove from left
                trim_count = len(self.portfolio_history) - entries_to_keep
                for _ in range(trim_count):
                    self.portfolio_history.popleft()
            else:
                # For list, slice to keep only the most recent entries
                if isinstance(self.portfolio_history, list):
                    self.portfolio_history[:] = self.portfolio_history[-entries_to_keep:]
                else:
                    # Fallback: convert to list, slice, and convert back
                    temp_list = list(self.portfolio_history)
                    self.portfolio_history.clear()
                    self.portfolio_history.extend(temp_list[-entries_to_keep:])
