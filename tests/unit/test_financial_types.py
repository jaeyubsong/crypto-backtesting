"""
Unit tests for financial data types and precision calculations.
Following TDD approach - testing Decimal-based financial calculations.
"""

from decimal import Decimal

import pytest

from src.core.types.financial import (
    FINANCIAL_PRECISION,
    ONE,
    PERCENTAGE_PRECISION,
    PRICE_PRECISION,
    ZERO,
    calculate_margin_needed,
    calculate_notional_value,
    calculate_pnl,
    round_amount,
    round_percentage,
    round_price,
    to_decimal,
)


class TestFinancialTypeConversions:
    """Test suite for financial type conversions."""

    def test_should_convert_float_to_decimal(self) -> None:
        """Test converting float to Decimal."""
        # Act
        result = to_decimal(50000.0)

        # Assert
        assert isinstance(result, Decimal)
        assert result == Decimal("50000.0")

    def test_should_convert_string_to_decimal(self) -> None:
        """Test converting string to Decimal."""
        # Act
        result = to_decimal("1.5")

        # Assert
        assert isinstance(result, Decimal)
        assert result == Decimal("1.5")

    def test_should_convert_int_to_decimal(self) -> None:
        """Test converting int to Decimal."""
        # Act
        result = to_decimal(100)

        # Assert
        assert isinstance(result, Decimal)
        assert result == Decimal("100")

    def test_should_return_decimal_unchanged(self) -> None:
        """Test that Decimal input is returned unchanged."""
        # Arrange
        original = Decimal("42.123456789")

        # Act
        result = to_decimal(original)

        # Assert
        assert result is original
        assert result == Decimal("42.123456789")


class TestFinancialRounding:
    """Test suite for financial rounding functions."""

    def test_should_round_price_to_two_decimals(self) -> None:
        """Test price rounding to 2 decimal places."""
        # Act
        result = round_price(Decimal("50000.123456"))

        # Assert
        assert result == Decimal("50000.12")
        assert result.as_tuple().exponent == PRICE_PRECISION.as_tuple().exponent

    def test_should_round_amount_to_eight_decimals(self) -> None:
        """Test amount rounding to 8 decimal places."""
        # Act
        result = round_amount(Decimal("1.123456789012345"))

        # Assert
        assert result == Decimal("1.12345679")
        assert result.as_tuple().exponent == FINANCIAL_PRECISION.as_tuple().exponent

    def test_should_round_percentage_to_four_decimals(self) -> None:
        """Test percentage rounding to 4 decimal places."""
        # Act
        result = round_percentage(Decimal("15.123456789"))

        # Assert
        assert result == Decimal("15.1235")
        assert result.as_tuple().exponent == PERCENTAGE_PRECISION.as_tuple().exponent

    def test_should_handle_exact_precision_values(self) -> None:
        """Test that already precise values are unchanged."""
        # Arrange
        exact_price = Decimal("50000.12")
        exact_amount = Decimal("1.12345678")

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
        result = calculate_notional_value(Decimal("1.5"), Decimal("50000.0"))

        # Assert
        assert result == Decimal("75000.00000000")
        assert isinstance(result, Decimal)

    def test_should_calculate_margin_needed_with_leverage(self) -> None:
        """Test margin calculation with leverage."""
        # Act
        result = calculate_margin_needed(Decimal("75000.0"), Decimal("5.0"))

        # Assert
        assert result == Decimal("15000.00000000")
        assert isinstance(result, Decimal)

    def test_should_raise_error_for_zero_leverage(self) -> None:
        """Test that zero leverage raises error."""
        # Act & Assert
        with pytest.raises(ValueError, match="Leverage must be positive"):
            calculate_margin_needed(Decimal("75000.0"), Decimal("0.0"))

    def test_should_raise_error_for_negative_leverage(self) -> None:
        """Test that negative leverage raises error."""
        # Act & Assert
        with pytest.raises(ValueError, match="Leverage must be positive"):
            calculate_margin_needed(Decimal("75000.0"), Decimal("-2.0"))

    def test_should_calculate_long_position_pnl(self) -> None:
        """Test PnL calculation for long position."""
        # Act
        result = calculate_pnl(
            entry_price=Decimal("50000.0"),
            exit_price=Decimal("52000.0"),
            amount=Decimal("1.5"),
            position_type="LONG",
        )

        # Assert
        assert result == Decimal("3000.00000000")  # (52000 - 50000) * 1.5
        assert isinstance(result, Decimal)

    def test_should_calculate_short_position_pnl(self) -> None:
        """Test PnL calculation for short position."""
        # Act
        result = calculate_pnl(
            entry_price=Decimal("50000.0"),
            exit_price=Decimal("48000.0"),
            amount=Decimal("1.0"),
            position_type="SHORT",
        )

        # Assert
        assert result == Decimal("2000.00000000")  # (50000 - 48000) * 1.0
        assert isinstance(result, Decimal)

    def test_should_calculate_negative_pnl_for_long_loss(self) -> None:
        """Test negative PnL calculation for long position loss."""
        # Act
        result = calculate_pnl(
            entry_price=Decimal("50000.0"),
            exit_price=Decimal("48000.0"),
            amount=Decimal("1.0"),
            position_type="LONG",
        )

        # Assert
        assert result == Decimal("-2000.00000000")  # (48000 - 50000) * 1.0
        assert isinstance(result, Decimal)

    def test_should_handle_absolute_amount_in_pnl(self) -> None:
        """Test that PnL calculation uses absolute amount."""
        # Act
        result = calculate_pnl(
            entry_price=Decimal("50000.0"),
            exit_price=Decimal("52000.0"),
            amount=Decimal("-1.5"),  # Negative amount
            position_type="LONG",
        )

        # Assert
        assert result == Decimal("3000.00000000")  # Uses abs(-1.5) = 1.5
        assert isinstance(result, Decimal)

    def test_should_raise_error_for_invalid_position_type(self) -> None:
        """Test that invalid position type raises error."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid position type"):
            calculate_pnl(Decimal("50000.0"), Decimal("52000.0"), Decimal("1.0"), "INVALID")


class TestFinancialPrecision:
    """Test suite for financial precision handling."""

    def test_should_handle_floating_point_precision_issues(self) -> None:
        """Test that Decimal avoids floating-point precision issues."""
        # Arrange - This would have precision issues with float
        price1 = 0.1
        price2 = 0.2
        expected_sum = 0.3

        # Act
        decimal_sum = to_decimal(price1) + to_decimal(price2)
        float_sum = price1 + price2

        # Assert - Decimal is precise, float is not
        assert decimal_sum == to_decimal(expected_sum)
        assert float_sum != expected_sum  # This is the float precision issue

    def test_should_maintain_precision_in_complex_calculations(self) -> None:
        """Test precision in complex financial calculations."""
        # Arrange
        entry_price = Decimal("50000.12345678")
        amount = Decimal("1.23456789")
        leverage = Decimal("5.5")

        # Act
        notional = calculate_notional_value(amount, entry_price)
        margin = calculate_margin_needed(notional, leverage)

        # Assert
        expected_notional = round_amount(entry_price * amount)
        expected_margin = round_amount(expected_notional / leverage)

        assert notional == expected_notional
        assert margin == expected_margin
        assert isinstance(notional, Decimal)
        assert isinstance(margin, Decimal)


class TestFinancialConstants:
    """Test suite for financial constants."""

    def test_financial_constants_are_decimals(self) -> None:
        """Test that financial constants are Decimal types."""
        # Assert
        assert isinstance(ZERO, Decimal)
        assert isinstance(ONE, Decimal)
        assert isinstance(FINANCIAL_PRECISION, Decimal)
        assert isinstance(PRICE_PRECISION, Decimal)
        assert isinstance(PERCENTAGE_PRECISION, Decimal)

    def test_constant_values(self) -> None:
        """Test constant values are correct."""
        # Assert
        assert Decimal("0") == ZERO
        assert Decimal("1") == ONE
        assert Decimal("0.00000001") == FINANCIAL_PRECISION
        assert Decimal("0.01") == PRICE_PRECISION
        assert Decimal("0.0001") == PERCENTAGE_PRECISION
