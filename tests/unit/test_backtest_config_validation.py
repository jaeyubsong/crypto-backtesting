"""
Unit tests for BacktestConfig automatic validation.
Testing fail-fast behavior in __post_init__ method.
"""

from datetime import UTC, datetime

import pytest

from src.core.enums import Symbol, Timeframe, TradingMode
from src.core.models.backtest import BacktestConfig


class TestBacktestConfigAutomaticValidation:
    """Test automatic validation in BacktestConfig.__post_init__."""

    def test_should_create_valid_backtest_config(self) -> None:
        """Test creating a valid BacktestConfig succeeds."""
        # Arrange & Act
        config = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 31, tzinfo=UTC),
            initial_capital=10000.0,
            trading_mode=TradingMode.FUTURES,
            max_leverage=10.0,
            maintenance_margin_rate=0.05,
        )

        # Assert
        assert config.symbol == Symbol.BTC
        assert config.initial_capital == 10000.0

    def test_should_raise_type_error_for_invalid_symbol(self) -> None:
        """Test that invalid symbol type raises TypeError."""
        # Act & Assert
        with pytest.raises(TypeError, match="symbol must be Symbol enum"):
            BacktestConfig(
                symbol="BTCUSDT",  # type: ignore[arg-type] # String instead of Symbol enum
                timeframe=Timeframe.H1,
                start_date=datetime(2024, 1, 1, tzinfo=UTC),
                end_date=datetime(2024, 1, 31, tzinfo=UTC),
                initial_capital=10000.0,
                trading_mode=TradingMode.FUTURES,
                max_leverage=10.0,
                maintenance_margin_rate=0.05,
            )

    def test_should_raise_type_error_for_invalid_timeframe(self) -> None:
        """Test that invalid timeframe type raises TypeError."""
        # Act & Assert
        with pytest.raises(TypeError, match="timeframe must be Timeframe enum"):
            BacktestConfig(
                symbol=Symbol.BTC,
                timeframe="1h",  # type: ignore[arg-type] # String instead of Timeframe enum
                start_date=datetime(2024, 1, 1, tzinfo=UTC),
                end_date=datetime(2024, 1, 31, tzinfo=UTC),
                initial_capital=10000.0,
                trading_mode=TradingMode.FUTURES,
                max_leverage=10.0,
                maintenance_margin_rate=0.05,
            )

    def test_should_raise_type_error_for_invalid_trading_mode(self) -> None:
        """Test that invalid trading mode type raises TypeError."""
        # Act & Assert
        with pytest.raises(TypeError, match="trading_mode must be TradingMode enum"):
            BacktestConfig(
                symbol=Symbol.BTC,
                timeframe=Timeframe.H1,
                start_date=datetime(2024, 1, 1, tzinfo=UTC),
                end_date=datetime(2024, 1, 31, tzinfo=UTC),
                initial_capital=10000.0,
                trading_mode="futures",  # type: ignore[arg-type] # String instead of TradingMode enum
                max_leverage=10.0,
                maintenance_margin_rate=0.05,
            )

    def test_should_raise_value_error_for_invalid_date_range(self) -> None:
        """Test that invalid date range raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid date range"):
            BacktestConfig(
                symbol=Symbol.BTC,
                timeframe=Timeframe.H1,
                start_date=datetime(2024, 1, 31, tzinfo=UTC),  # After end_date
                end_date=datetime(2024, 1, 1, tzinfo=UTC),
                initial_capital=10000.0,
                trading_mode=TradingMode.FUTURES,
                max_leverage=10.0,
                maintenance_margin_rate=0.05,
            )

    def test_should_raise_value_error_for_invalid_capital(self) -> None:
        """Test that invalid initial capital raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid initial capital"):
            BacktestConfig(
                symbol=Symbol.BTC,
                timeframe=Timeframe.H1,
                start_date=datetime(2024, 1, 1, tzinfo=UTC),
                end_date=datetime(2024, 1, 31, tzinfo=UTC),
                initial_capital=-1000.0,  # Negative capital
                trading_mode=TradingMode.FUTURES,
                max_leverage=10.0,
                maintenance_margin_rate=0.05,
            )

    def test_should_raise_value_error_for_invalid_leverage(self) -> None:
        """Test that invalid leverage raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid leverage"):
            BacktestConfig(
                symbol=Symbol.BTC,
                timeframe=Timeframe.H1,
                start_date=datetime(2024, 1, 1, tzinfo=UTC),
                end_date=datetime(2024, 1, 31, tzinfo=UTC),
                initial_capital=10000.0,
                trading_mode=TradingMode.SPOT,
                max_leverage=10.0,  # High leverage not allowed in SPOT
                maintenance_margin_rate=0.05,
            )

    def test_should_raise_value_error_for_invalid_margin_rate(self) -> None:
        """Test that invalid maintenance margin rate raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid maintenance margin rate"):
            BacktestConfig(
                symbol=Symbol.BTC,
                timeframe=Timeframe.H1,
                start_date=datetime(2024, 1, 1, tzinfo=UTC),
                end_date=datetime(2024, 1, 31, tzinfo=UTC),
                initial_capital=10000.0,
                trading_mode=TradingMode.FUTURES,
                max_leverage=10.0,
                maintenance_margin_rate=0.15,  # 15% - too high
            )

    def test_should_raise_value_error_for_negative_margin_rate(self) -> None:
        """Test that negative maintenance margin rate raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid maintenance margin rate"):
            BacktestConfig(
                symbol=Symbol.BTC,
                timeframe=Timeframe.H1,
                start_date=datetime(2024, 1, 1, tzinfo=UTC),
                end_date=datetime(2024, 1, 31, tzinfo=UTC),
                initial_capital=10000.0,
                trading_mode=TradingMode.FUTURES,
                max_leverage=10.0,
                maintenance_margin_rate=-0.01,  # Negative rate
            )

    def test_should_allow_zero_maintenance_margin_rate(self) -> None:
        """Test that zero maintenance margin rate is allowed."""
        # Arrange & Act
        config = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 31, tzinfo=UTC),
            initial_capital=10000.0,
            trading_mode=TradingMode.FUTURES,
            max_leverage=10.0,
            maintenance_margin_rate=0.0,  # Zero rate should be allowed
        )

        # Assert
        assert config.maintenance_margin_rate == 0.0

    def test_should_allow_max_maintenance_margin_rate(self) -> None:
        """Test that maximum maintenance margin rate is allowed."""
        # Arrange & Act
        config = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 31, tzinfo=UTC),
            initial_capital=10000.0,
            trading_mode=TradingMode.FUTURES,
            max_leverage=10.0,
            maintenance_margin_rate=0.1,  # 10% - maximum allowed
        )

        # Assert
        assert config.maintenance_margin_rate == 0.1
