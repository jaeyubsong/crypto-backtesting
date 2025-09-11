"""
Unit tests for validation utilities and resource limits.
"""

import pytest

from src.core.constants import MAX_POSITIONS_PER_PORTFOLIO, MAX_TRADE_SIZE, MIN_TRADE_SIZE
from src.core.enums import Symbol
from src.core.exceptions.backtest import ValidationError
from src.core.utils.validation import (
    validate_margin_rate,
    validate_percentage,
    validate_positive,
    validate_symbol,
)


class TestValidationUtils:
    """Test validation utility functions."""

    def test_should_validate_symbol_correctly(self) -> None:
        """Test Symbol validation."""
        # Valid symbol
        assert validate_symbol(Symbol.BTC) == Symbol.BTC
        assert validate_symbol(Symbol.ETH) == Symbol.ETH

    def test_should_reject_invalid_symbol_type(self) -> None:
        """Test Symbol validation rejects wrong types."""
        with pytest.raises(TypeError, match="symbol must be Symbol enum"):
            validate_symbol("BTCUSDT")

        with pytest.raises(TypeError, match="symbol must be Symbol enum"):
            validate_symbol(123)

        with pytest.raises(TypeError, match="symbol must be Symbol enum"):
            validate_symbol(None)

    def test_should_validate_positive_values(self) -> None:
        """Test positive value validation."""
        assert validate_positive(1.0, "price") == 1.0
        assert validate_positive(0.001, "amount") == 0.001
        assert validate_positive(100000, "leverage") == 100000

    def test_should_reject_non_positive_values(self) -> None:
        """Test positive validation rejects invalid values."""
        with pytest.raises(ValidationError, match="price must be positive"):
            validate_positive(0, "price")

        with pytest.raises(ValidationError, match="amount must be positive"):
            validate_positive(-10, "amount")

    def test_should_validate_percentage(self) -> None:
        """Test percentage validation."""
        assert validate_percentage(50.0) == 50.0
        assert validate_percentage(100.0) == 100.0
        assert validate_percentage(0.1) == 0.1

    def test_should_reject_invalid_percentage(self) -> None:
        """Test percentage validation rejects invalid values."""
        with pytest.raises(ValidationError, match="percentage must be between 0 and 100"):
            validate_percentage(0)

        with pytest.raises(ValidationError, match="percentage must be between 0 and 100"):
            validate_percentage(101)

        with pytest.raises(ValidationError, match="percentage must be between 0 and 100"):
            validate_percentage(-10)

    def test_should_validate_margin_rate(self) -> None:
        """Test margin rate validation."""
        assert validate_margin_rate(0.0) == 0.0
        assert validate_margin_rate(0.5) == 0.5
        assert validate_margin_rate(1.0) == 1.0

    def test_should_reject_invalid_margin_rate(self) -> None:
        """Test margin rate validation rejects invalid values."""
        with pytest.raises(ValidationError, match="margin_rate must be between 0 and 1"):
            validate_margin_rate(-0.1)

        with pytest.raises(ValidationError, match="margin_rate must be between 0 and 1"):
            validate_margin_rate(1.1)


class TestTradeSizeLimits:
    """Test trade size limits."""

    def test_should_respect_min_trade_size(self) -> None:
        """Test that MIN_TRADE_SIZE is enforced."""
        # This constant should be defined
        assert MIN_TRADE_SIZE > 0
        assert MIN_TRADE_SIZE < 1  # Should be small for dust trades

    def test_should_respect_max_trade_size(self) -> None:
        """Test that MAX_TRADE_SIZE is reasonable."""
        assert MAX_TRADE_SIZE > 1000  # Should allow large trades
        assert MAX_TRADE_SIZE < 1e10  # But not infinite

    def test_should_respect_max_positions_limit(self) -> None:
        """Test that position limit is reasonable."""
        assert MAX_POSITIONS_PER_PORTFOLIO > 10  # Allow multiple positions
        assert MAX_POSITIONS_PER_PORTFOLIO <= 1000  # But not unlimited
