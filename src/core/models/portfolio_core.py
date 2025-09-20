"""
Portfolio core state management.

This module handles the fundamental portfolio state and basic operations,
following the Single Responsibility Principle for state management.
"""

import threading
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.core.constants import (
    MAX_PORTFOLIO_HISTORY,
    PORTFOLIO_HISTORY_TRIM_TO,
)
from src.core.enums import Symbol, TradingMode
from src.core.models.position import Position
from src.core.models.trade import Trade

# to_float import removed - no longer needed for float-to-float conversions
from .portfolio_helpers import PortfolioValidator


@dataclass
class PortfolioCore:
    """Core portfolio state management.

    Handles the fundamental state of a portfolio including capital,
    positions, trade history, and portfolio snapshots.

    Thread Safety:
        This class is thread-safe. All state-modifying operations
        (add_position, remove_position, record_snapshot) use an internal
        RLock to ensure atomic operations and prevent race conditions.
        Read-only operations are safe to call concurrently.
    """

    initial_capital: float
    cash: float
    positions: dict[Symbol, Position]
    trades: deque[Trade]
    portfolio_history: deque[dict[str, Any]]
    trading_mode: TradingMode
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        """Financial values are already float - no conversion needed."""
        # Values are already float type, no conversion needed
        pass

    def available_margin(self) -> float:
        """Calculate available margin for new positions."""
        return self.cash

    def used_margin(self) -> float:
        """Calculate total margin used by open positions."""
        return sum((position.margin_used for position in self.positions.values()), 0.0)

    def realized_pnl(self) -> float:
        """Calculate total realized PnL from completed trades."""
        return sum((trade.pnl for trade in self.trades), 0.0)

    def unrealized_pnl(self, current_prices: Mapping[Symbol, float]) -> float:
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
        with self._lock:
            # Use centralized validator for position validation
            PortfolioValidator.validate_position_for_add(position, len(self.positions))

            # Check margin requirement
            PortfolioValidator.validate_margin_requirement(
                position.margin_used, self.cash, "opening position"
            )

            self.positions[position.symbol] = position
            self.cash = self.cash - position.margin_used

    def remove_position(self, symbol: Symbol) -> Position:
        """Remove and return a position from the portfolio.

        Args:
            symbol: Symbol of position to remove

        Returns:
            The removed position

        Raises:
            ValidationError: If position not found
        """
        with self._lock:
            # Use centralized validator for existence check
            PortfolioValidator.validate_position_exists(symbol, self.positions)

            return self.positions.pop(symbol)

    def record_snapshot(self, timestamp: datetime, current_prices: Mapping[Symbol, float]) -> None:
        """Record portfolio state at given timestamp.

        This method is thread-safe and can be called concurrently.

        Args:
            timestamp: Current timestamp
            current_prices: Current market prices for all symbols
        """
        from .portfolio_metrics import PortfolioMetrics

        with self._lock:
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

                # Efficient bulk trimming for deque: create new deque with recent entries
                # This is O(entries_to_keep) instead of O(trim_count) for loop-based popleft()
                recent_entries = list(self.portfolio_history)[-entries_to_keep:]
                self.portfolio_history.clear()
                self.portfolio_history.extend(recent_entries)
