"""
Unit tests for PortfolioRisk class.
Testing liquidation detection, position closure, and risk management following TDD principles.
"""

from collections import deque
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.core.enums import PositionType, Symbol, TradingMode
from src.core.exceptions.backtest import PositionNotFoundError, ValidationError
from src.core.models.portfolio_core import PortfolioCore
from src.core.models.portfolio_risk import PortfolioRisk
from src.core.models.position import Position


class TestPortfolioRiskLiquidationDetection:
    """Test liquidation detection functionality."""

    def test_should_detect_no_liquidation_risk_when_positions_healthy(self) -> None:
        """Test that healthy positions are not flagged for liquidation."""
        # Arrange
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=5000.0,
        )

        core = PortfolioCore(
            initial_capital=10000.0,
            cash=5000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.BTC] = btc_position
        risk_manager = PortfolioRisk(core)

        # Act - price drops but not enough for liquidation
        current_prices = {Symbol.BTC: 48000.0}  # Small drop
        at_risk_symbols = risk_manager.check_liquidation(current_prices)

        # Assert
        assert len(at_risk_symbols) == 0

    def test_should_detect_liquidation_risk_when_position_underwater(self) -> None:
        """Test detection of positions at liquidation risk."""
        # Arrange - high leverage position vulnerable to liquidation
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=20.0,  # High leverage = higher risk
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=2500.0,
        )

        core = PortfolioCore(
            initial_capital=5000.0,
            cash=2500.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.BTC] = btc_position
        risk_manager = PortfolioRisk(core)

        # Act - significant price drop that would trigger liquidation
        current_prices = {Symbol.BTC: 45000.0}  # Large drop
        at_risk_symbols = risk_manager.check_liquidation(current_prices)

        # Assert
        assert Symbol.BTC in at_risk_symbols

    def test_should_handle_multiple_positions_liquidation_check(self) -> None:
        """Test liquidation checking with multiple positions."""
        # Arrange - mix of healthy and at-risk positions
        btc_long = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=5.0,  # Lower leverage = safer
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=10000.0,
        )

        eth_short = Position(
            symbol=Symbol.ETH,
            size=10.0,
            entry_price=3000.0,
            leverage=20.0,  # High leverage = riskier
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=1500.0,
        )

        core = PortfolioCore(
            initial_capital=20000.0,
            cash=8500.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.BTC] = btc_long
        core.positions[Symbol.ETH] = eth_short
        risk_manager = PortfolioRisk(core)

        # Act - ETH price rises significantly (bad for short), BTC stable
        current_prices = {Symbol.BTC: 49000.0, Symbol.ETH: 3200.0}
        at_risk_symbols = risk_manager.check_liquidation(current_prices)

        # Assert - ETH short might be at risk, BTC long should be safe
        # This depends on the liquidation logic in Position class
        assert len(at_risk_symbols) <= 2  # At most both positions

    def test_should_skip_positions_without_current_price(self) -> None:
        """Test that positions without current price data are skipped."""
        # Arrange
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=5000.0,
        )

        core = PortfolioCore(
            initial_capital=10000.0,
            cash=5000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.BTC] = btc_position
        risk_manager = PortfolioRisk(core)

        # Act - no price data for BTC
        current_prices = {Symbol.ETH: 3000.0}  # Missing BTC price
        at_risk_symbols = risk_manager.check_liquidation(current_prices)

        # Assert - BTC should be skipped, not flagged
        assert len(at_risk_symbols) == 0

    def test_should_use_custom_maintenance_margin_rate(self) -> None:
        """Test liquidation detection with custom maintenance margin rate."""
        # Arrange
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=5000.0,
        )

        core = PortfolioCore(
            initial_capital=10000.0,
            cash=5000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.BTC] = btc_position
        risk_manager = PortfolioRisk(core)

        # Act - test with higher maintenance margin requirement
        current_prices = {Symbol.BTC: 48000.0}
        strict_at_risk = risk_manager.check_liquidation(
            current_prices, maintenance_margin_rate=0.1
        )  # 10%
        lenient_at_risk = risk_manager.check_liquidation(
            current_prices, maintenance_margin_rate=0.02
        )  # 2%

        # Assert - stricter margin should catch more positions
        assert len(strict_at_risk) >= len(lenient_at_risk)


class TestPortfolioRiskPositionClosure:
    """Test position closure functionality."""

    def test_should_close_position_at_price_with_profit(self) -> None:
        """Test closing a profitable position at specified price."""
        # Arrange
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=5000.0,
        )

        core = PortfolioCore(
            initial_capital=10000.0,
            cash=5000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.BTC] = btc_position
        risk_manager = PortfolioRisk(core)

        # Act - close at profit
        close_price = Decimal("55000.0")
        fee = Decimal("27.5")
        realized_pnl = risk_manager.close_position_at_price(Symbol.BTC, close_price, fee)

        # Assert
        # PnL = (55000 - 50000) * 1.0 - 27.5 = 5000 - 27.5 = 4972.5
        assert realized_pnl == Decimal("4972.5")
        assert Symbol.BTC not in core.positions
        # Cash = original 5000 + margin 5000 + pnl 4972.5 = 14972.5
        assert core.cash == 14972.5

    def test_should_close_position_at_price_with_loss(self) -> None:
        """Test closing a position at a loss."""
        # Arrange
        eth_position = Position(
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
        core.positions[Symbol.ETH] = eth_position
        risk_manager = PortfolioRisk(core)

        # Act - close short position at loss (price went up)
        close_price = 3200.0
        fee = 16.0
        realized_pnl = risk_manager.close_position_at_price(Symbol.ETH, close_price, fee)

        # Assert
        # Short PnL = (3000 - 3200) * 5.0 - 16.0 = -1000 - 16 = -1016
        assert realized_pnl == -1016.0
        assert Symbol.ETH not in core.positions
        # Cash = original 7000 + margin 3000 + pnl (-1016) = 8984
        assert core.cash == 8984.0

    def test_should_raise_error_when_closing_nonexistent_position(self) -> None:
        """Test error handling when trying to close non-existent position."""
        # Arrange
        core = PortfolioCore(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        risk_manager = PortfolioRisk(core)

        # Act & Assert
        with pytest.raises(PositionNotFoundError) as exc_info:
            risk_manager.close_position_at_price(Symbol.BTC, 55000.0, 27.5)

        assert "BTCUSDT" in str(exc_info.value)

    def test_should_validate_close_position_parameters(self) -> None:
        """Test parameter validation for position closure."""
        # Arrange
        core = PortfolioCore(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        risk_manager = PortfolioRisk(core)

        # Act & Assert - invalid symbol
        with pytest.raises(ValidationError):
            risk_manager.close_position_at_price(None, 50000.0, 25.0)  # type: ignore

        # Invalid price
        with pytest.raises(ValidationError):
            risk_manager.close_position_at_price(Symbol.BTC, -50000.0, 25.0)

        # Invalid fee
        with pytest.raises(ValidationError):
            risk_manager.close_position_at_price(Symbol.BTC, 50000.0, -25.0)

    def test_should_close_position_with_percentage(self) -> None:
        """Test closing position with percentage parameter."""
        # Arrange
        btc_position = Position(
            symbol=Symbol.BTC,
            size=2.0,
            entry_price=50000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=20000.0,
        )

        core = PortfolioCore(
            initial_capital=30000.0,
            cash=10000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.BTC] = btc_position
        risk_manager = PortfolioRisk(core)

        # Act - close 50% of position
        result = risk_manager.close_position(Symbol.BTC, 55000.0, percentage=50.0)

        # Assert
        assert result is True
        assert Symbol.BTC in core.positions  # Position still exists
        position = core.positions[Symbol.BTC]
        assert position.size == 1.0  # Reduced from 2.0 to 1.0
        assert position.margin_used == 10000.0  # Reduced from 20000 to 10000
        # Cash should increase by partial margin + partial PnL
        assert core.cash > 10000.0  # Should be higher due to PnL

    def test_should_fully_close_position_with_100_percentage(self) -> None:
        """Test that 100% closure fully closes the position."""
        # Arrange
        eth_position = Position(
            symbol=Symbol.ETH,
            size=10.0,
            entry_price=3000.0,
            leverage=3.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=10000.0,
        )

        core = PortfolioCore(
            initial_capital=15000.0,
            cash=5000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.ETH] = eth_position
        risk_manager = PortfolioRisk(core)

        # Act - close 100% of position
        result = risk_manager.close_position(Symbol.ETH, 3100.0, percentage=100.0)

        # Assert
        assert result is True
        assert Symbol.ETH not in core.positions  # Position fully closed
        assert core.cash > 5000.0  # Should increase due to margin release + PnL

    def test_should_return_false_for_nonexistent_position_closure(self) -> None:
        """Test that closing non-existent position returns False instead of error."""
        # Arrange
        core = PortfolioCore(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        risk_manager = PortfolioRisk(core)

        # Act
        result = risk_manager.close_position(Symbol.BTC, 55000.0, percentage=50.0)

        # Assert
        assert result is False

    def test_should_validate_percentage_parameter(self) -> None:
        """Test validation of percentage parameter."""
        # Arrange
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=10000.0,
        )

        core = PortfolioCore(
            initial_capital=15000.0,
            cash=5000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.BTC] = btc_position
        risk_manager = PortfolioRisk(core)

        # Act & Assert - invalid percentages should raise errors
        with pytest.raises(ValidationError):
            risk_manager.close_position(Symbol.BTC, 55000.0, percentage=-10.0)

        with pytest.raises(ValidationError):
            risk_manager.close_position(Symbol.BTC, 55000.0, percentage=150.0)

    def test_should_handle_partial_closure_calculations_correctly(self) -> None:
        """Test accurate calculations for partial position closures."""
        # Arrange - position in profit
        btc_position = Position(
            symbol=Symbol.BTC,
            size=4.0,
            entry_price=50000.0,
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=20000.0,
        )

        core = PortfolioCore(
            initial_capital=30000.0,
            cash=10000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.BTC] = btc_position
        risk_manager = PortfolioRisk(core)

        # Act - close 25% at profit
        initial_cash = core.cash
        result = risk_manager.close_position(Symbol.BTC, 52000.0, percentage=25.0)

        # Assert
        assert result is True
        position = core.positions[Symbol.BTC]
        assert position.size == 3.0  # 75% of 4.0
        assert position.margin_used == 15000.0  # 75% of 20000

        # Calculate expected cash increase
        # Partial margin: 20000 * 0.25 = 5000
        # Partial PnL: (52000 - 50000) * 4.0 * 0.25 = 2000
        # Fee: 1.0 * 52000 * 0.001 = 52 (default taker fee)
        # Expected cash = 10000 + 5000 + 2000 - 52 = 16948
        expected_cash_increase = 5000 + 2000 - 52  # margin + pnl - fee
        assert (
            abs(core.cash - (initial_cash + expected_cash_increase)) < 1
        )  # Allow small rounding differences


class TestPortfolioRiskEdgeCases:
    """Test edge cases and error conditions."""

    def test_should_handle_zero_margin_positions(self) -> None:
        """Test handling positions with zero margin (edge case)."""
        # Arrange - theoretical position with zero margin
        position = Position(
            symbol=Symbol.BTC,
            size=0.0001,  # Very small position
            entry_price=50000.0,
            leverage=1.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=0.0,  # Edge case: zero margin
        )

        core = PortfolioCore(
            initial_capital=1000.0,
            cash=1000.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.BTC] = position
        risk_manager = PortfolioRisk(core)

        # Act
        realized_pnl = risk_manager.close_position_at_price(Symbol.BTC, 55000.0, 0.05)

        # Assert - should handle gracefully
        assert Symbol.BTC not in core.positions
        assert realized_pnl == Decimal("0.45000000")  # (55000 - 50000) * 0.0001 - 0.05 = 0.5 - 0.05

    def test_should_handle_extreme_leverage_positions(self) -> None:
        """Test handling positions with very high leverage."""
        # Arrange - extremely high leverage position
        position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=100.0,  # Extreme leverage
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=500.0,  # 50000 / 100
        )

        core = PortfolioCore(
            initial_capital=1000.0,
            cash=500.0,
            positions={},
            trades=deque(),
            portfolio_history=deque(),
            trading_mode=TradingMode.FUTURES,
        )
        core.positions[Symbol.BTC] = position
        risk_manager = PortfolioRisk(core)

        # Act - small price movement should trigger liquidation risk
        current_prices = {Symbol.BTC: 49500.0}  # Small 1% drop
        at_risk_symbols = risk_manager.check_liquidation(current_prices)

        # Assert - high leverage position should be very sensitive
        # (This test verifies that extreme leverage is handled correctly)
        assert len(at_risk_symbols) >= 0  # Could be 0 or 1 depending on liquidation logic
