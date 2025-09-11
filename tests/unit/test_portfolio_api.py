"""
Unit tests for Portfolio API methods (PRD Section 3.2).
Tests the getter methods and snapshot recording functionality.
"""

from datetime import UTC, datetime

import pytest

from src.core.enums import PositionType, Symbol, TradingMode
from src.core.exceptions.backtest import ValidationError
from src.core.models.portfolio import Portfolio
from src.core.models.position import Position


class TestPortfolioGetterMethods:
    """Test Portfolio getter API methods."""

    def test_should_get_position_size_for_long_position(self) -> None:
        """Test get_position_size returns positive for long position."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=2.0,
            entry_price=50000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=20000.0,
        )

        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=80000.0,
            positions={Symbol.BTC: btc_position},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.FUTURES,
        )

        assert portfolio.get_position_size(Symbol.BTC) == 2.0

    def test_should_get_position_size_for_short_position(self) -> None:
        """Test get_position_size returns negative for short position."""
        eth_position = Position(
            symbol=Symbol.ETH,
            size=-5.0,
            entry_price=3000.0,
            leverage=3.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=5000.0,
        )

        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=95000.0,
            positions={Symbol.ETH: eth_position},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.FUTURES,
        )

        assert portfolio.get_position_size(Symbol.ETH) == -5.0

    def test_should_get_zero_for_nonexistent_position(self) -> None:
        """Test get_position_size returns 0 when no position exists."""
        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=100000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        assert portfolio.get_position_size(Symbol.BTC) == 0.0

    def test_should_reject_invalid_symbol_in_get_position_size(self) -> None:
        """Test get_position_size validates symbol type."""
        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=100000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        with pytest.raises(TypeError, match="symbol must be Symbol enum"):
            portfolio.get_position_size("BTCUSDT")  # type: ignore

    def test_should_get_cash(self) -> None:
        """Test get_cash returns current cash balance."""
        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=75000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.FUTURES,
        )

        assert portfolio.get_cash() == 75000.0

    def test_should_get_margin_ratio_for_spot_trading(self) -> None:
        """Test get_margin_ratio returns 0 for spot trading."""
        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=100000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        assert portfolio.get_margin_ratio() == 0.0

    def test_should_get_margin_ratio_for_futures_with_positions(self) -> None:
        """Test get_margin_ratio calculates correctly for futures."""
        position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=5000.0,
        )

        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=95000.0,
            positions={Symbol.BTC: position},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.FUTURES,
        )

        # Margin ratio = used_margin / initial_capital = 5000 / 100000 = 0.05
        assert portfolio.get_margin_ratio() == 0.05

    def test_should_get_margin_ratio_zero_when_no_positions(self) -> None:
        """Test get_margin_ratio returns 0 when no positions."""
        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=100000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.FUTURES,
        )

        assert portfolio.get_margin_ratio() == 0.0

    def test_should_get_unrealized_pnl_for_existing_position(self) -> None:
        """Test get_unrealized_pnl returns PnL for position."""
        position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=25000.0,
        )

        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=75000.0,
            positions={Symbol.BTC: position},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.FUTURES,
        )

        # Long position: PnL = (55000 - 50000) * 1.0 = 5000
        assert portfolio.get_unrealized_pnl(Symbol.BTC, 55000.0) == 5000.0

    def test_should_get_zero_unrealized_pnl_for_nonexistent_position(self) -> None:
        """Test get_unrealized_pnl returns 0 when no position."""
        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=100000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        assert portfolio.get_unrealized_pnl(Symbol.BTC, 55000.0) == 0.0

    def test_should_validate_inputs_in_get_unrealized_pnl(self) -> None:
        """Test get_unrealized_pnl validates inputs."""
        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=100000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        # Invalid symbol
        with pytest.raises(TypeError, match="symbol must be Symbol enum"):
            portfolio.get_unrealized_pnl("BTCUSDT", 50000.0)  # type: ignore

        # Invalid price
        with pytest.raises(ValidationError, match="current_price must be positive"):
            portfolio.get_unrealized_pnl(Symbol.BTC, -50000.0)

    def test_should_get_leverage_for_existing_position(self) -> None:
        """Test get_leverage returns leverage for position."""
        position = Position(
            symbol=Symbol.ETH,
            size=10.0,
            entry_price=3000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=6000.0,
        )

        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=94000.0,
            positions={Symbol.ETH: position},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.FUTURES,
        )

        assert portfolio.get_leverage(Symbol.ETH) == 5.0

    def test_should_get_zero_leverage_for_nonexistent_position(self) -> None:
        """Test get_leverage returns 0 when no position."""
        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=100000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        assert portfolio.get_leverage(Symbol.BTC) == 0.0

    def test_should_validate_symbol_in_get_leverage(self) -> None:
        """Test get_leverage validates symbol type."""
        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=100000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        with pytest.raises(TypeError, match="symbol must be Symbol enum"):
            portfolio.get_leverage("ETHUSDT")  # type: ignore


class TestPortfolioSnapshotRecording:
    """Test Portfolio snapshot recording functionality."""

    def test_should_record_portfolio_snapshot(self) -> None:
        """Test record_snapshot captures portfolio state."""
        position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=2.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=25000.0,
        )

        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=75000.0,
            positions={Symbol.BTC: position},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.FUTURES,
        )

        timestamp = datetime.now(UTC)
        current_prices = {Symbol.BTC: 52000.0}

        portfolio.record_snapshot(timestamp, current_prices)

        assert len(portfolio.portfolio_history) == 1
        snapshot = portfolio.portfolio_history[0]

        assert snapshot["timestamp"] == timestamp
        assert snapshot["portfolio_value"] == 77000.0  # 75000 cash + 2000 unrealized PnL
        assert snapshot["cash"] == 75000.0
        assert snapshot["unrealized_pnl"] == 2000.0
        assert snapshot["realized_pnl"] == 0.0
        assert snapshot["margin_used"] == 25000.0
        assert snapshot["positions"] == 1
        assert snapshot["leverage_ratio"] == 0.25  # 25000 / 100000

    def test_should_record_snapshot_for_spot_trading(self) -> None:
        """Test record_snapshot works for spot trading."""
        position = Position(
            symbol=Symbol.BTC,
            size=2.0,
            entry_price=50000.0,
            leverage=1.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=0.0,  # No margin in spot
        )

        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=0.0,  # All cash used to buy BTC
            positions={Symbol.BTC: position},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        timestamp = datetime.now(UTC)
        current_prices = {Symbol.BTC: 55000.0}

        portfolio.record_snapshot(timestamp, current_prices)

        snapshot = portfolio.portfolio_history[0]
        assert snapshot["portfolio_value"] == 110000.0  # 0 cash + 2 * 55000
        assert snapshot["leverage_ratio"] == 0.0  # No leverage in spot

    def test_should_trim_history_when_exceeding_limit(self) -> None:
        """Test record_snapshot trims history when too large."""
        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=100000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        # Create a history near the limit
        for i in range(99999):
            portfolio.portfolio_history.append({"index": i})

        assert len(portfolio.portfolio_history) == 99999

        # Record one more snapshot (should not trigger trimming yet)
        portfolio.record_snapshot(datetime.now(UTC), {})
        assert len(portfolio.portfolio_history) == 100000

        # Record another snapshot (should trigger trimming)
        portfolio.record_snapshot(datetime.now(UTC), {})
        assert len(portfolio.portfolio_history) == 50001  # Trimmed to 50k + 1 new

        # Check that old entries were removed
        assert portfolio.portfolio_history[0]["index"] == 50000

    def test_should_record_multiple_snapshots_over_time(self) -> None:
        """Test recording multiple snapshots maintains chronological order."""
        portfolio = Portfolio(
            initial_capital=100000.0,
            cash=100000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        timestamps = [
            datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC),
            datetime(2025, 1, 1, 11, 0, 0, tzinfo=UTC),
            datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        ]

        for ts in timestamps:
            portfolio.record_snapshot(ts, {})

        assert len(portfolio.portfolio_history) == 3
        for i, ts in enumerate(timestamps):
            assert portfolio.portfolio_history[i]["timestamp"] == ts
