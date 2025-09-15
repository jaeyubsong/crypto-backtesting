"""
Unit tests for utility decorators.
Following TDD approach - testing validation, logging, and position requirement decorators.
"""
# ruff: noqa: ARG001

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from src.core.enums import Symbol
from src.core.exceptions.backtest import ValidationError
from src.core.utils.decorators import log_trades, require_position, validate_inputs


class TestValidateInputsDecorator:
    """Test suite for @validate_inputs decorator."""

    def test_should_validate_symbol_parameter(self) -> None:
        """Test that symbol parameter is validated."""

        @validate_inputs
        def test_function(symbol: Symbol, amount: float) -> bool:
            return True

        # Should pass with valid Symbol
        result = test_function(Symbol.BTC, 1.0)
        assert result is True

        # Should raise error with invalid symbol (using a non-Symbol value)
        with pytest.raises(ValidationError, match="Invalid symbol"):
            test_function("INVALID", 1.0)  # type: ignore[arg-type]

    def test_should_validate_amount_parameter(self) -> None:
        """Test that amount parameter is validated."""

        @validate_inputs
        def test_function(symbol: Symbol, amount: float) -> bool:
            return True

        # Should pass with positive amount
        result = test_function(Symbol.BTC, 1.5)
        assert result is True

        # Should raise error with zero amount
        with pytest.raises(ValidationError, match="amount must be positive"):
            test_function(Symbol.BTC, 0.0)

        # Should raise error with negative amount
        with pytest.raises(ValidationError, match="amount must be positive"):
            test_function(Symbol.BTC, -1.0)

    def test_should_validate_price_parameter(self) -> None:
        """Test that price parameter is validated."""

        @validate_inputs
        def test_function(symbol: Symbol, amount: float, price: float) -> bool:
            return True

        # Should pass with positive price
        result = test_function(Symbol.BTC, 1.0, 50000.0)
        assert result is True

        # Should raise error with zero price
        with pytest.raises(ValidationError, match="price must be positive"):
            test_function(Symbol.BTC, 1.0, 0.0)

    def test_should_validate_leverage_parameter(self) -> None:
        """Test that leverage parameter is validated."""

        @validate_inputs
        def test_function(symbol: Symbol, leverage: float) -> bool:
            return True

        # Should pass with positive leverage
        result = test_function(Symbol.BTC, 2.5)
        assert result is True

        # Should raise error with zero leverage
        with pytest.raises(ValidationError, match="leverage must be positive"):
            test_function(Symbol.BTC, 0.0)

    def test_should_skip_none_values(self) -> None:
        """Test that None values are skipped in validation."""

        @validate_inputs
        def test_function(symbol: Symbol | None = None, amount: float | None = None) -> bool:
            return True

        # Should not raise error with None values
        result = test_function()
        assert result is True

    def test_should_preserve_function_metadata(self) -> None:
        """Test that decorator preserves function metadata."""

        @validate_inputs
        def original_function(symbol: Symbol, amount: float) -> bool:
            """Original function docstring."""
            return True

        assert original_function.__name__ == "original_function"
        assert (
            original_function.__doc__ is not None
            and "Original function docstring" in original_function.__doc__
        )


class TestLogTradesDecorator:
    """Test suite for @log_trades decorator."""

    @patch("loguru.logger")
    def test_should_log_function_entry_and_success(self, mock_logger: Mock) -> None:
        """Test that decorator logs function entry and successful completion."""

        @log_trades
        def test_function(symbol: Symbol, amount: float) -> bool:
            return True

        # Execute function
        result = test_function(Symbol.BTC, 1.5)

        # Verify result
        assert result is True

        # Verify logging calls
        assert mock_logger.info.call_count == 1
        assert mock_logger.success.call_count == 1

        # Check entry log call
        entry_call = mock_logger.info.call_args
        assert "Trading operation started: test_function" in entry_call[0][0]
        entry_context = entry_call[1]["extra"]
        assert "correlation_id" in entry_context
        assert entry_context["symbol"] == "BTCUSDT"
        assert entry_context["amount"] == 1.5

        # Check success log call
        success_call = mock_logger.success.call_args
        assert "Trading operation completed: test_function" in success_call[0][0]
        success_context = success_call[1]["extra"]
        assert success_context["success"] is True
        assert "execution_time_ms" in success_context
        assert success_context["result"] is True

    @patch("loguru.logger")
    def test_should_log_function_failure(self, mock_logger: Mock) -> None:
        """Test that decorator logs function failures with error context."""

        @log_trades
        def test_function(symbol: Symbol, amount: float) -> bool:
            raise ValueError("Test error")

        # Execute function and expect exception
        with pytest.raises(ValueError, match="Test error"):
            test_function(Symbol.BTC, 1.5)

        # Verify logging calls
        assert mock_logger.info.call_count == 1
        assert mock_logger.error.call_count == 1

        # Check error log call
        error_call = mock_logger.error.call_args
        assert "Trading operation failed: test_function" in error_call[0][0]
        error_context = error_call[1]["extra"]
        assert error_context["success"] is False
        assert error_context["error_type"] == "ValueError"
        assert error_context["error_message"] == "Test error"
        assert "execution_time_ms" in error_context

    @patch("loguru.logger")
    def test_should_handle_decimal_parameters(self, mock_logger: Mock) -> None:
        """Test that decorator properly handles Decimal parameters."""

        @log_trades
        def test_function(symbol: Symbol, amount: Decimal, price: Decimal) -> bool:
            return True

        # Execute with Decimal parameters
        amount = Decimal("1.50000000")
        price = Decimal("50000.12")
        result = test_function(Symbol.BTC, amount, price)

        # Verify result
        assert result is True

        # Check that Decimal values are properly serialized
        entry_call = mock_logger.info.call_args
        entry_context = entry_call[1]["extra"]
        assert entry_context["amount"] == "1.50000000"
        assert entry_context["price"] == "50000.12"

    @patch("loguru.logger")
    def test_should_generate_unique_correlation_ids(self, mock_logger: Mock) -> None:
        """Test that each function call gets a unique correlation ID."""

        @log_trades
        def test_function() -> bool:
            return True

        # Execute function multiple times
        test_function()
        test_function()

        # Get correlation IDs from both calls
        call1_context = mock_logger.info.call_args_list[0][1]["extra"]
        call2_context = mock_logger.info.call_args_list[1][1]["extra"]

        # Verify they are different
        assert call1_context["correlation_id"] != call2_context["correlation_id"]
        assert len(call1_context["correlation_id"]) == 8  # Truncated UUID


class TestRequirePositionDecorator:
    """Test suite for @require_position decorator."""

    def test_should_allow_execution_when_position_exists(self) -> None:
        """Test that function executes when position exists."""

        # Mock object with positions
        mock_self = Mock()
        mock_self.positions = {Symbol.BTC: Mock()}

        @require_position("symbol")
        def test_function(self: object, symbol: Symbol) -> bool:
            return True

        # Should execute successfully
        result = test_function(mock_self, Symbol.BTC)
        assert result is True

    def test_should_raise_error_when_position_missing(self) -> None:
        """Test that function raises error when position doesn't exist."""

        # Mock object without positions
        mock_self = Mock()
        mock_self.positions = {}

        @require_position("symbol")
        def test_function(self: object, symbol: Symbol) -> bool:
            return True

        # Should raise ValidationError
        with pytest.raises(ValidationError, match="No position exists for symbol"):
            test_function(mock_self, Symbol.BTC)

    def test_should_handle_missing_positions_attribute(self) -> None:
        """Test that function executes when self has no positions attribute."""

        # Mock object without positions attribute
        mock_self = Mock(spec=[])  # Empty spec means no attributes

        @require_position("symbol")
        def test_function(self: object, symbol: Symbol) -> bool:
            return True

        # Should execute successfully (no positions attribute means no check)
        result = test_function(mock_self, Symbol.BTC)
        assert result is True

    def test_should_work_with_custom_symbol_parameter_name(self) -> None:
        """Test that decorator works with custom symbol parameter name."""

        mock_self = Mock()
        mock_self.positions = {Symbol.ETH: Mock()}

        @require_position("trading_symbol")
        def test_function(self: object, trading_symbol: Symbol) -> bool:
            return True

        # Should execute successfully
        result = test_function(mock_self, Symbol.ETH)
        assert result is True

        # Should raise error for missing position
        with pytest.raises(ValidationError, match="No position exists for symbol"):
            test_function(mock_self, Symbol.BTC)


class TestDecoratorCombination:
    """Test suite for combining multiple decorators."""

    @patch("loguru.logger")
    def test_should_work_when_decorators_combined(self, mock_logger: Mock) -> None:
        """Test that multiple decorators work together."""

        mock_self = Mock()
        mock_self.positions = {Symbol.BTC: Mock()}

        @log_trades
        @validate_inputs
        @require_position("symbol")
        def test_function(self: object, symbol: Symbol, amount: float) -> bool:
            return True

        # Should execute successfully with all validations
        result = test_function(mock_self, Symbol.BTC, 1.5)
        assert result is True

        # Verify logging occurred
        assert mock_logger.info.call_count == 1
        assert mock_logger.success.call_count == 1

    def test_should_fail_early_with_combined_validations(self) -> None:
        """Test that validation errors are caught early in decorator chain."""

        mock_self = Mock()
        mock_self.positions = {Symbol.BTC: Mock()}

        @require_position("symbol")
        @validate_inputs
        def test_function(self: object, symbol: Symbol, amount: float) -> bool:
            return True

        # Should fail at validation step before position check
        with pytest.raises(ValidationError, match="amount must be positive"):
            test_function(mock_self, Symbol.BTC, 0.0)
