"""
Unit tests for financial data types and precision calculations.
Following TDD approach - testing float-based financial calculations.
"""

import pytest

from src.core.types.financial import (
    FINANCIAL_DECIMALS,
    ONE,
    PERCENTAGE_DECIMALS,
    PRICE_DECIMALS,
    ZERO,
    calculate_margin_needed,
    calculate_notional_value,
    calculate_pnl,
    round_amount,
    round_percentage,
    round_price,
    to_float,
)


class TestFinancialTypeConversions:
    """Test suite for financial type conversions."""

    def test_should_return_float_unchanged(self) -> None:
        """Test that float input is returned unchanged."""
        # Act
        result = to_float(50000.0)

        # Assert
        assert isinstance(result, float)
        assert result == 50000.0

    def test_should_convert_string_to_float(self) -> None:
        """Test converting string to float."""
        # Act
        result = to_float("1.5")

        # Assert
        assert isinstance(result, float)
        assert result == 1.5

    def test_should_convert_int_to_float(self) -> None:
        """Test converting int to float."""
        # Act
        result = to_float(100)

        # Assert
        assert isinstance(result, float)
        assert result == 100.0

    def test_should_convert_various_numeric_types(self) -> None:
        """Test converting various numeric types to float."""
        # Test int
        assert to_float(42) == 42.0
        # Test string
        assert to_float("42.123456789") == 42.123456789
        # Test float
        assert to_float(42.5) == 42.5


class TestFinancialRounding:
    """Test suite for financial rounding functions."""

    def test_should_round_price_to_two_decimals(self) -> None:
        """Test price rounding to 2 decimal places."""
        # Act
        result = round_price(50000.123456)

        # Assert
        assert result == 50000.12
        # Check decimal places by converting to string
        assert str(result) == "50000.12"

    def test_should_round_amount_to_eight_decimals(self) -> None:
        """Test amount rounding to 8 decimal places."""
        # Act
        result = round_amount(float("1.123456789012345"))

        # Assert
        assert result == 1.12345679
        # Check precision by string representation
        assert f"{result:.8f}" == "1.12345679"

    def test_should_round_percentage_to_four_decimals(self) -> None:
        """Test percentage rounding to 4 decimal places."""
        # Act
        result = round_percentage(float("15.123456789"))

        # Assert
        assert result == 15.1235
        # Check precision by string representation
        assert f"{result:.4f}" == "15.1235"

    def test_should_handle_exact_precision_values(self) -> None:
        """Test that already precise values are unchanged."""
        # Arrange
        exact_price = float("50000.12")
        exact_amount = float("1.12345678")

        # Act
        price_result = round_price(exact_price)
        amount_result = round_amount(exact_amount)

        # Assert
        assert price_result == exact_price
        assert amount_result == exact_amount


class TestFinancialCalculations:
    """Test suite for financial calculation functions."""

    def test_should_calculate_notional_value(self) -> None:
        """Test notional value calculation with precision."""
        # Act
        result = calculate_notional_value(float("1.5"), float("50000.0"))

        # Assert
        assert result == float("75000.00000000")
        assert isinstance(result, float)

    def test_should_calculate_margin_needed_with_leverage(self) -> None:
        """Test margin calculation with leverage."""
        # Act
        result = calculate_margin_needed(float("75000.0"), float("5.0"))

        # Assert
        assert result == float("15000.00000000")
        assert isinstance(result, float)

    def test_should_raise_error_for_zero_leverage(self) -> None:
        """Test that zero leverage raises error."""
        # Act & Assert
        with pytest.raises(ValueError, match="Leverage must be positive"):
            calculate_margin_needed(float("75000.0"), float("0.0"))

    def test_should_raise_error_for_negative_leverage(self) -> None:
        """Test that negative leverage raises error."""
        # Act & Assert
        with pytest.raises(ValueError, match="Leverage must be positive"):
            calculate_margin_needed(float("75000.0"), float("-2.0"))

    def test_should_calculate_long_position_pnl(self) -> None:
        """Test PnL calculation for long position."""
        # Act
        result = calculate_pnl(
            entry_price=float("50000.0"),
            exit_price=float("52000.0"),
            amount=float("1.5"),
            position_type="LONG",
        )

        # Assert
        assert result == float("3000.00000000")  # (52000 - 50000) * 1.5
        assert isinstance(result, float)

    def test_should_calculate_short_position_pnl(self) -> None:
        """Test PnL calculation for short position."""
        # Act
        result = calculate_pnl(
            entry_price=float("50000.0"),
            exit_price=float("48000.0"),
            amount=float("1.0"),
            position_type="SHORT",
        )

        # Assert
        assert result == float("2000.00000000")  # (50000 - 48000) * 1.0
        assert isinstance(result, float)

    def test_should_calculate_negative_pnl_for_long_loss(self) -> None:
        """Test negative PnL calculation for long position loss."""
        # Act
        result = calculate_pnl(
            entry_price=float("50000.0"),
            exit_price=float("48000.0"),
            amount=float("1.0"),
            position_type="LONG",
        )

        # Assert
        assert result == float("-2000.00000000")  # (48000 - 50000) * 1.0
        assert isinstance(result, float)

    def test_should_handle_absolute_amount_in_pnl(self) -> None:
        """Test that PnL calculation uses absolute amount."""
        # Act
        result = calculate_pnl(
            entry_price=float("50000.0"),
            exit_price=float("52000.0"),
            amount=float("-1.5"),  # Negative amount
            position_type="LONG",
        )

        # Assert
        assert result == float("3000.00000000")  # Uses abs(-1.5) = 1.5
        assert isinstance(result, float)

    def test_should_raise_error_for_invalid_position_type(self) -> None:
        """Test that invalid position type raises error."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid position type"):
            calculate_pnl(float("50000.0"), float("52000.0"), float("1.0"), "INVALID")


class TestFinancialPrecision:
    """Test suite for financial precision handling."""

    def test_should_handle_floating_point_precision_issues(self) -> None:
        """Test that we're aware of floating-point precision limitations."""
        # Arrange - Known floating-point precision issue
        price1 = 0.1
        price2 = 0.2
        expected_sum = 0.3

        # Act
        float_sum = price1 + price2
        rounded_sum = round(float_sum, 10)  # Round to 10 decimal places

        # Assert - Acknowledge float precision limitations
        # Direct comparison may fail due to floating-point representation
        assert abs(float_sum - expected_sum) < 1e-10  # Within tolerance
        assert rounded_sum == expected_sum  # Rounding fixes the issue

    def test_should_maintain_precision_in_complex_calculations(self) -> None:
        """Test precision in complex financial calculations."""
        # Arrange
        entry_price = float("50000.12345678")
        amount = float("1.23456789")
        leverage = float("5.5")

        # Act
        notional = calculate_notional_value(amount, entry_price)
        margin = calculate_margin_needed(notional, leverage)

        # Assert
        expected_notional = round_amount(entry_price * amount)
        expected_margin = round_amount(expected_notional / leverage)

        assert notional == expected_notional
        assert margin == expected_margin
        assert isinstance(notional, float)
        assert isinstance(margin, float)


class TestFinancialConstants:
    """Test suite for financial constants."""

    def test_financial_constants_are_decimals(self) -> None:
        """Test that financial constants are float types."""
        # Assert
        assert isinstance(ZERO, float)
        assert isinstance(ONE, float)
        assert isinstance(FINANCIAL_DECIMALS, int)
        assert isinstance(PRICE_DECIMALS, int)
        assert isinstance(PERCENTAGE_DECIMALS, int)

    def test_constant_values(self) -> None:
        """Test constant values are correct."""
        # Assert
        assert ZERO == 0.0
        assert ONE == 1.0
        assert FINANCIAL_DECIMALS == 8
        assert PRICE_DECIMALS == 2
        assert PERCENTAGE_DECIMALS == 4
