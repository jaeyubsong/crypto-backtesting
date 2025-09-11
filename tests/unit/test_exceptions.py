"""
Unit tests for custom exceptions.
Testing all exception classes and their attributes.
"""

from src.core.exceptions.backtest import (
    BacktestException,
    DataError,
    InsufficientFundsError,
    InvalidLeverageError,
    LiquidationError,
    PositionNotFoundError,
    StrategyError,
    ValidationError,
)


class TestBacktestException:
    """Tests for BacktestException base class."""

    def test_should_create_base_exception_with_message(self) -> None:
        """Test creating base exception with message."""
        exc = BacktestException("Test error message")
        assert str(exc) == "Test error message"
        assert isinstance(exc, Exception)


class TestValidationError:
    """Tests for ValidationError."""

    def test_should_create_validation_error_with_message(self) -> None:
        """Test creating validation error."""
        exc = ValidationError("Invalid input provided")
        assert str(exc) == "Invalid input provided"
        assert isinstance(exc, BacktestException)

    def test_should_handle_field_specific_validation(self) -> None:
        """Test validation error with field information."""
        exc = ValidationError("Price must be positive, got -100")
        assert "Price" in str(exc)
        assert "-100" in str(exc)


class TestDataError:
    """Tests for DataError."""

    def test_should_create_data_error_with_message(self) -> None:
        """Test creating data error."""
        exc = DataError("Failed to load CSV file")
        assert str(exc) == "Failed to load CSV file"
        assert isinstance(exc, BacktestException)

    def test_should_handle_file_path_in_message(self) -> None:
        """Test data error with file path."""
        exc = DataError("File not found: /data/btc.csv")
        assert "/data/btc.csv" in str(exc)


class TestStrategyError:
    """Tests for StrategyError."""

    def test_should_create_strategy_error_with_message(self) -> None:
        """Test creating strategy error."""
        exc = StrategyError("Strategy execution failed")
        assert str(exc) == "Strategy execution failed"
        assert isinstance(exc, BacktestException)

    def test_should_handle_strategy_name_in_message(self) -> None:
        """Test strategy error with strategy name."""
        exc = StrategyError("Strategy 'MovingAverage' raised exception")
        assert "MovingAverage" in str(exc)


class TestInsufficientFundsError:
    """Tests for InsufficientFundsError."""

    def test_should_create_insufficient_funds_error(self) -> None:
        """Test creating insufficient funds error with all attributes."""
        exc = InsufficientFundsError(
            required=10000.0, available=5000.0, operation="opening long position"
        )

        assert exc.required == 10000.0
        assert exc.available == 5000.0
        assert exc.operation == "opening long position"
        assert isinstance(exc, BacktestException)

    def test_should_format_error_message_correctly(self) -> None:
        """Test that error message is formatted correctly."""
        exc = InsufficientFundsError(required=10000.0, available=5000.0, operation="buying BTC")

        message = str(exc)
        assert "10000" in message
        assert "5000" in message
        assert "buying BTC" in message
        assert "Insufficient funds" in message

    def test_should_handle_zero_available_funds(self) -> None:
        """Test error with zero available funds."""
        exc = InsufficientFundsError(required=1000.0, available=0.0, operation="margin call")

        assert exc.available == 0.0
        message = str(exc)
        assert "0" in message or "0.0" in message


class TestPositionNotFoundError:
    """Tests for PositionNotFoundError."""

    def test_should_create_position_not_found_error(self) -> None:
        """Test creating position not found error."""
        exc = PositionNotFoundError("BTCUSDT")

        assert exc.symbol == "BTCUSDT"
        assert isinstance(exc, BacktestException)

    def test_should_format_error_message_with_symbol(self) -> None:
        """Test that error message includes symbol."""
        exc = PositionNotFoundError("ETHUSDT")

        message = str(exc)
        assert "ETHUSDT" in message
        assert "Position not found" in message

    def test_should_handle_various_symbol_formats(self) -> None:
        """Test error with different symbol formats."""
        exc1 = PositionNotFoundError("BTC")
        exc2 = PositionNotFoundError("ETH/USDT")

        assert "BTC" in str(exc1)
        assert "ETH/USDT" in str(exc2)


class TestInvalidLeverageError:
    """Tests for InvalidLeverageError."""

    def test_should_create_invalid_leverage_error(self) -> None:
        """Test creating invalid leverage error."""
        exc = InvalidLeverageError(leverage=150.0, mode="futures", max_leverage=125.0)

        assert exc.leverage == 150.0
        assert exc.max_leverage == 125.0
        assert exc.mode == "futures"
        assert isinstance(exc, BacktestException)

    def test_should_format_error_message_with_details(self) -> None:
        """Test that error message includes all details."""
        exc = InvalidLeverageError(leverage=15.0, mode="margin", max_leverage=10.0)

        message = str(exc)
        assert "15" in message
        assert "10" in message
        assert "margin" in message
        assert "Invalid leverage" in message

    def test_should_handle_spot_trading_leverage(self) -> None:
        """Test error for spot trading with leverage > 1."""
        exc = InvalidLeverageError(leverage=2.0, mode="spot", max_leverage=1.0)

        message = str(exc)
        assert "spot" in message
        assert "1" in message


class TestLiquidationError:
    """Tests for LiquidationError."""

    def test_should_create_liquidation_error(self) -> None:
        """Test creating liquidation error."""
        exc = LiquidationError(symbol="BTCUSDT", loss=5000.0, reason="margin call")

        assert exc.symbol == "BTCUSDT"
        assert exc.loss == 5000.0
        assert exc.reason == "margin call"
        assert isinstance(exc, BacktestException)

    def test_should_format_error_message_with_position_details(self) -> None:
        """Test that error message includes position details."""
        exc = LiquidationError(symbol="ETHUSDT", loss=10000.0, reason="insufficient margin")

        message = str(exc)
        assert "ETHUSDT" in message
        assert "10000" in message
        assert "insufficient margin" in message
        assert "liquidated" in message.lower()

    def test_should_handle_short_position_liquidation(self) -> None:
        """Test liquidation error for short position."""
        exc = LiquidationError(symbol="BTCUSDT", loss=2500.0, reason="price moved against position")

        assert exc.loss == 2500.0
        message = str(exc)
        assert "2500" in message
        assert "price moved against position" in message
