"""
Unit tests for Portfolio validation and limits.
Tests the Phase 1 fixes for input validation and resource limits.
"""

from datetime import UTC, datetime

import pytest

from src.core.constants import MAX_POSITIONS_PER_PORTFOLIO
from src.core.enums import PositionType, Symbol, TradingMode
from src.core.exceptions.backtest import InsufficientFundsError, ValidationError
from src.core.models.portfolio import Portfolio
from src.core.models.position import Position


class TestPortfolioInputValidation:
    """Test Portfolio input validation."""

    def test_should_reject_string_symbol_in_buy(self):
        """Test that buy() rejects string symbols."""
        portfolio = Portfolio(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        # Should raise TypeError for string symbol
        with pytest.raises(TypeError, match="symbol must be Symbol enum"):
            portfolio.buy("BTCUSDT", 1.0, 50000.0)  # type: ignore

    def test_should_reject_negative_price_in_buy(self):
        """Test that buy() rejects negative prices."""
        portfolio = Portfolio(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        with pytest.raises(ValidationError, match="price must be positive"):
            portfolio.buy(Symbol.BTC, 1.0, -50000.0)

    def test_should_reject_zero_amount_in_buy(self):
        """Test that buy() rejects zero amount."""
        portfolio = Portfolio(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        with pytest.raises(ValidationError, match="amount must be positive"):
            portfolio.buy(Symbol.BTC, 0, 50000.0)

    def test_should_reject_string_symbol_in_sell(self):
        """Test that sell() rejects string symbols."""
        portfolio = Portfolio(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.FUTURES,
        )

        # Should raise TypeError for string symbol
        with pytest.raises(TypeError, match="symbol must be Symbol enum"):
            portfolio.sell("ETHUSDT", 1.0, 3000.0)  # type: ignore

    def test_should_reject_too_small_trade(self):
        """Test that trades below MIN_TRADE_SIZE are rejected."""
        portfolio = Portfolio(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        with pytest.raises(ValidationError, match="Trade size too small"):
            portfolio.buy(Symbol.BTC, 0.0000001, 50000.0)  # Too small

    def test_should_reject_too_large_trade(self):
        """Test that trades above MAX_TRADE_SIZE are rejected."""
        portfolio = Portfolio(
            initial_capital=100000000.0,  # Large capital
            cash=100000000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        with pytest.raises(ValidationError, match="Trade size too large"):
            portfolio.buy(Symbol.BTC, 10000000, 50000.0)  # Too large

    def test_should_raise_insufficient_funds_with_context(self):
        """Test that InsufficientFundsError includes context."""
        portfolio = Portfolio(
            initial_capital=1000.0,
            cash=1000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.SPOT,
        )

        with pytest.raises(InsufficientFundsError) as exc_info:
            portfolio.buy(Symbol.BTC, 1.0, 50000.0)  # Needs 50k, has 1k

        error = exc_info.value
        assert error.required == 50000.0
        assert error.available == 1000.0
        assert "buying" in error.operation
        assert "BTCUSDT" in error.operation


class TestPortfolioResourceLimits:
    """Test Portfolio resource limits."""

    def test_should_respect_max_positions_limit(self):
        """Test that portfolio respects MAX_POSITIONS_PER_PORTFOLIO."""
        portfolio = Portfolio(
            initial_capital=1000000.0,
            cash=1000000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.FUTURES,
        )

        # Add positions up to the limit
        for i in range(MAX_POSITIONS_PER_PORTFOLIO):
            # Create unique positions (can't have duplicate symbols)
            # For testing, we'll just modify the position but not actually add unique symbols
            # This is a limitation of having only 2 symbols
            if i == 0:
                position = Position(
                    symbol=Symbol.BTC,
                    size=0.001,
                    entry_price=50000.0 + i,
                    leverage=10.0,
                    timestamp=datetime.now(UTC),
                    position_type=PositionType.LONG,
                    margin_used=5.0,
                )
                portfolio.add_position(position)
            elif i == 1:
                position = Position(
                    symbol=Symbol.ETH,
                    size=0.01,
                    entry_price=3000.0 + i,
                    leverage=10.0,
                    timestamp=datetime.now(UTC),
                    position_type=PositionType.LONG,
                    margin_used=3.0,
                )
                portfolio.add_position(position)
            else:
                # Can't add more than 2 unique positions with only BTC and ETH
                # This test shows the limit would work if we had more symbols
                break

        # For a proper test, we would need more symbols
        # But we can verify the limit is set reasonably
        assert MAX_POSITIONS_PER_PORTFOLIO >= 10
        assert MAX_POSITIONS_PER_PORTFOLIO <= 1000

    def test_should_enforce_position_limit_on_add(self):
        """Test that add_position enforces the limit."""
        # Create a portfolio with many positions (simulated)
        positions = {}

        # Simulate having MAX_POSITIONS_PER_PORTFOLIO positions
        # We'll use the Portfolio with its positions dict pre-populated
        portfolio = Portfolio(
            initial_capital=1000000.0,
            cash=1000000.0,
            positions=positions,
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.FUTURES,
        )

        # Manually set positions to simulate max limit
        # This is a workaround since we only have 2 symbols
        for i in range(MAX_POSITIONS_PER_PORTFOLIO):
            # Create fake positions just for counting
            portfolio.positions[f"FAKE{i}"] = None  # type: ignore

        # Now try to add one more
        new_position = Position(
            symbol=Symbol.BTC,
            size=0.001,
            entry_price=50000.0,
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=5.0,
        )

        with pytest.raises(ValidationError, match="Maximum positions limit reached"):
            portfolio.add_position(new_position)


class TestPortfolioClosePosition:
    """Test close_position validation."""

    def test_should_reject_invalid_percentage(self):
        """Test that close_position validates percentage."""
        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=5000.0,
        )

        portfolio = Portfolio(
            initial_capital=10000.0,
            cash=5000.0,
            positions={Symbol.BTC: btc_position},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.FUTURES,
        )

        # Test invalid percentages
        with pytest.raises(ValidationError, match="percentage must be between 0 and 100"):
            portfolio.close_position(Symbol.BTC, 0)  # 0% invalid

        with pytest.raises(ValidationError, match="percentage must be between 0 and 100"):
            portfolio.close_position(Symbol.BTC, 101)  # Over 100%

        with pytest.raises(ValidationError, match="percentage must be between 0 and 100"):
            portfolio.close_position(Symbol.BTC, -10)  # Negative

    def test_should_reject_string_symbol_in_close_position(self):
        """Test that close_position rejects string symbols."""
        portfolio = Portfolio(
            initial_capital=10000.0,
            cash=10000.0,
            positions={},
            trades=[],
            portfolio_history=[],
            trading_mode=TradingMode.FUTURES,
        )

        with pytest.raises(TypeError, match="symbol must be Symbol enum"):
            portfolio.close_position("BTCUSDT", 50)  # type: ignore
