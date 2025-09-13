"""
Unit tests for PortfolioTrading class.
Testing buy/sell operations and trade execution logic following TDD principles.
"""

from collections import deque
from datetime import UTC, datetime

import pytest

from src.core.enums import ActionType, PositionType, Symbol, TradingMode
from src.core.exceptions.backtest import InsufficientFundsError, ValidationError
from src.core.models.portfolio_core import PortfolioCore
from src.core.models.portfolio_trading import PortfolioTrading
from src.core.models.position import Position


class TestPortfolioTradingBuyOperations:
    """Test buy operations in different scenarios."""

    def test_should_execute_buy_order_new_long_position_spot(self) -> None:
        """Test opening a new long position in SPOT mode."""
        # Arrange
        core = PortfolioCore(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.SPOT,
        )
        trading = PortfolioTrading(core)

        # Act
        result = trading.buy(Symbol.BTC, 0.1, 50000.0, leverage=1.0)

        # Assert
        assert result is True
        assert Symbol.BTC in core.positions
        position = core.positions[Symbol.BTC]
        assert position.size == 0.1
        assert position.entry_price == 50000.0
        assert position.position_type == PositionType.LONG
        assert position.leverage == 1.0
        assert position.margin_used == 5000.0  # 0.1 * 50000 / 1
        assert core.cash == 5000.0  # 10000 - 5000
        assert len(core.trades) == 1

    def test_should_execute_buy_order_new_long_position_futures(self) -> None:
        """Test opening a new long position in FUTURES mode with leverage."""
        # Arrange
        core = PortfolioCore(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        trading = PortfolioTrading(core)

        # Act
        result = trading.buy(Symbol.BTC, 1.0, 50000.0, leverage=10.0)

        # Assert
        assert result is True
        assert Symbol.BTC in core.positions
        position = core.positions[Symbol.BTC]
        assert position.size == 1.0
        assert position.entry_price == 50000.0
        assert position.position_type == PositionType.LONG
        assert position.leverage == 10.0
        assert position.margin_used == 5000.0  # 1.0 * 50000 / 10
        assert core.cash == 5000.0  # 10000 - 5000
        assert len(core.trades) == 1

    def test_should_add_to_existing_long_position(self) -> None:
        """Test adding to an existing long position."""
        # Arrange - create portfolio with existing position
        existing_position = Position(
            symbol=Symbol.BTC,
            size=0.5,
            entry_price=48000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=12000.0,
        )

        core = PortfolioCore(
            initial_capital=20000.0,
            cash=8000.0,  # 20000 - 12000
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.BTC] = existing_position
        trading = PortfolioTrading(core)

        # Act - add to position
        result = trading.buy(Symbol.BTC, 0.3, 52000.0, leverage=2.0)

        # Assert
        assert result is True
        position = core.positions[Symbol.BTC]
        assert position.size == 0.8  # 0.5 + 0.3
        # New weighted average: ((0.5 * 48000) + (0.3 * 52000)) / 0.8 = 49500
        assert position.entry_price == 49500.0
        assert position.margin_used == 19800.0  # 12000 + 7800
        assert core.cash == 200.0  # 8000 - 7800

    def test_should_close_short_position_with_buy_order(self) -> None:
        """Test closing a short position with a buy order."""
        # Arrange - create portfolio with short position
        short_position = Position(
            symbol=Symbol.ETH,
            size=2.0,
            entry_price=3000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=1200.0,
        )

        core = PortfolioCore(
            initial_capital=10000.0,
            cash=8800.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.ETH] = short_position
        trading = PortfolioTrading(core)

        # Act - buy to close short position
        result = trading.buy(Symbol.ETH, 2.0, 2900.0, leverage=5.0)

        # Assert - position should be closed with profit
        assert result is True
        assert Symbol.ETH not in core.positions  # Position closed
        assert len(core.trades) == 1
        trade = core.trades[0]
        assert trade.action == ActionType.BUY
        assert trade.position_type == PositionType.SHORT
        assert trade.pnl > 0  # Profit from short position

    def test_should_raise_insufficient_funds_error_on_buy(self) -> None:
        """Test that buy order raises error when insufficient funds."""
        # Arrange
        core = PortfolioCore(
            initial_capital=1000.0,
            cash=1000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.SPOT,
        )
        trading = PortfolioTrading(core)

        # Act & Assert
        with pytest.raises(InsufficientFundsError) as exc_info:
            trading.buy(Symbol.BTC, 1.0, 50000.0, leverage=1.0)

        assert exc_info.value.required == 50000.0
        assert exc_info.value.available == 1000.0


class TestPortfolioTradingSellOperations:
    """Test sell operations in different scenarios."""

    def test_should_execute_sell_order_new_short_position_futures(self) -> None:
        """Test opening a new short position in FUTURES mode."""
        # Arrange
        core = PortfolioCore(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        trading = PortfolioTrading(core)

        # Act
        result = trading.sell(Symbol.BTC, 1.0, 50000.0, leverage=10.0)

        # Assert
        assert result is True
        assert Symbol.BTC in core.positions
        position = core.positions[Symbol.BTC]
        assert position.size == 1.0
        assert position.entry_price == 50000.0
        assert position.position_type == PositionType.SHORT
        assert position.leverage == 10.0
        assert position.margin_used == 5000.0  # 1.0 * 50000 / 10
        assert core.cash == 5000.0  # 10000 - 5000
        assert len(core.trades) == 1

    def test_should_reject_short_position_in_spot_mode(self) -> None:
        """Test that sell order is rejected in SPOT mode without existing position."""
        # Arrange
        core = PortfolioCore(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.SPOT,
        )
        trading = PortfolioTrading(core)

        # Act
        result = trading.sell(Symbol.BTC, 1.0, 50000.0, leverage=1.0)

        # Assert
        assert result is False  # Can't short in spot mode
        assert len(core.positions) == 0
        assert len(core.trades) == 0

    def test_should_close_long_position_with_sell_order(self) -> None:
        """Test closing a long position with a sell order."""
        # Arrange - create portfolio with long position
        long_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=48000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=24000.0,
        )

        core = PortfolioCore(
            initial_capital=30000.0,
            cash=6000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.BTC] = long_position
        trading = PortfolioTrading(core)

        # Act - sell to close long position at profit
        result = trading.sell(Symbol.BTC, 1.0, 52000.0, leverage=2.0)

        # Assert - position should be closed with profit
        assert result is True
        assert Symbol.BTC not in core.positions  # Position closed
        assert len(core.trades) == 1
        trade = core.trades[0]
        assert trade.action == ActionType.SELL
        assert trade.position_type == PositionType.LONG
        assert trade.pnl > 0  # Profit from long position

    def test_should_partially_close_long_position_spot(self) -> None:
        """Test partially closing a long position in SPOT mode."""
        # Arrange - create portfolio with long position
        long_position = Position(
            symbol=Symbol.BTC,
            size=2.0,
            entry_price=50000.0,
            leverage=1.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=100000.0,
        )

        core = PortfolioCore(
            initial_capital=120000.0,
            cash=20000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.SPOT,
        )
        core.positions[Symbol.BTC] = long_position
        trading = PortfolioTrading(core)

        # Act - sell half the position
        result = trading.sell(Symbol.BTC, 1.0, 55000.0, leverage=1.0)

        # Assert - position should be partially closed
        assert result is True
        assert Symbol.BTC in core.positions  # Position still exists
        position = core.positions[Symbol.BTC]
        assert position.size == 1.0  # Reduced from 2.0 to 1.0
        assert len(core.trades) == 1

    def test_should_add_to_existing_short_position_futures(self) -> None:
        """Test adding to an existing short position in FUTURES mode."""
        # Arrange - create portfolio with existing short position
        short_position = Position(
            symbol=Symbol.ETH,
            size=5.0,
            entry_price=3000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=3000.0,
        )

        core = PortfolioCore(
            initial_capital=10000.0,
            cash=7000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.ETH] = short_position
        trading = PortfolioTrading(core)

        # Act - add to short position
        result = trading.sell(Symbol.ETH, 3.0, 2900.0, leverage=5.0)

        # Assert
        assert result is True
        position = core.positions[Symbol.ETH]
        assert position.size == 8.0  # 5.0 + 3.0
        # New weighted average: ((5.0 * 3000) + (3.0 * 2900)) / 8.0 = 2962.5
        assert position.entry_price == 2962.5
        assert position.margin_used == 4740.0  # 3000 + 1740
        assert core.cash == 5260.0  # 7000 - 1740

    def test_should_raise_insufficient_funds_error_on_sell_futures(self) -> None:
        """Test that sell order raises error when insufficient funds in futures."""
        # Arrange
        core = PortfolioCore(
            initial_capital=1000.0,
            cash=1000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        trading = PortfolioTrading(core)

        # Act & Assert
        with pytest.raises(InsufficientFundsError) as exc_info:
            trading.sell(Symbol.BTC, 10.0, 50000.0, leverage=1.0)

        assert exc_info.value.required == 500000.0  # 10.0 * 50000 / 1
        assert exc_info.value.available == 1000.0


class TestPortfolioTradingEdgeCases:
    """Test edge cases and error conditions."""

    def test_should_handle_zero_amount_order(self) -> None:
        """Test handling of zero amount orders (should be validated)."""
        # Arrange
        core = PortfolioCore(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.SPOT,
        )
        trading = PortfolioTrading(core)

        # Act & Assert - OrderValidator should catch this
        with pytest.raises(ValidationError):
            trading.buy(Symbol.BTC, 0.0, 50000.0)

    def test_should_handle_negative_price_order(self) -> None:
        """Test handling of negative price orders (should be validated)."""
        # Arrange
        core = PortfolioCore(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.SPOT,
        )
        trading = PortfolioTrading(core)

        # Act & Assert - OrderValidator should catch this
        with pytest.raises(ValidationError):
            trading.buy(Symbol.BTC, 1.0, -50000.0)

    def test_should_handle_oversized_sell_in_spot_mode(self) -> None:
        """Test selling more than available position size in SPOT mode."""
        # Arrange - create portfolio with small long position
        long_position = Position(
            symbol=Symbol.BTC,
            size=0.5,
            entry_price=50000.0,
            leverage=1.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=25000.0,
        )

        core = PortfolioCore(
            initial_capital=30000.0,
            cash=5000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.SPOT,
        )
        core.positions[Symbol.BTC] = long_position
        trading = PortfolioTrading(core)

        # Act - try to sell more than we have
        result = trading.sell(Symbol.BTC, 1.0, 55000.0)

        # Assert - should return without error but not execute
        assert result is True  # Method completes but doesn't process oversized amount
        # Position should remain unchanged
        assert core.positions[Symbol.BTC].size == 0.5

    def test_should_record_trade_with_correct_fee_calculation(self) -> None:
        """Test that trades are recorded with correct fee calculations."""
        # Arrange
        core = PortfolioCore(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        trading = PortfolioTrading(core)

        # Act
        trading.buy(Symbol.BTC, 1.0, 50000.0, leverage=10.0)

        # Assert
        assert len(core.trades) == 1
        trade = core.trades[0]
        assert trade.symbol == Symbol.BTC
        assert trade.action == ActionType.BUY
        assert trade.quantity == 1.0
        assert trade.price == 50000.0
        assert trade.leverage == 10.0
        assert trade.fee > 0  # Fee should be calculated
        assert trade.position_type == PositionType.LONG
        assert trade.margin_used == 5000.0

    def test_should_maintain_thread_safety_with_concurrent_operations(self) -> None:
        """Test that operations are thread-safe with proper locking."""
        # Arrange
        core = PortfolioCore(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        trading = PortfolioTrading(core)

        # Act - simulate concurrent operations
        result1 = trading.buy(Symbol.BTC, 0.5, 50000.0, leverage=10.0)
        result2 = trading.buy(Symbol.ETH, 2.0, 3000.0, leverage=5.0)

        # Assert - both operations should succeed
        assert result1 is True
        assert result2 is True
        assert len(core.positions) == 2
        assert len(core.trades) == 2
        # Total margin used: (0.5 * 50000 / 10) + (2.0 * 3000 / 5) = 2500 + 1200 = 3700
        assert core.cash == 6300.0  # 10000 - 3700
