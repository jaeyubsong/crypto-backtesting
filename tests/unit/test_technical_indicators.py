"""
Unit tests for Technical Indicators Calculator.

Tests cover Strategy Pattern implementation, indicator calculations,
and extensibility for the technical_indicators module.
"""

import numpy as np
import pandas as pd
import pytest

from src.infrastructure.data.technical_indicators import (
    BollingerBandsStrategy,
    MACDStrategy,
    MovingAverageStrategy,
    RSIStrategy,
    TechnicalIndicatorsCalculator,
    VWAPStrategy,
    calculate_basic_indicators,
    create_technical_indicators_calculator,
)


class TestTechnicalIndicators:
    """Test suite for technical indicators."""

    @pytest.fixture
    def sample_ohlcv_data(self) -> pd.DataFrame:
        """Create sample OHLCV data for testing."""
        # Create realistic price data with some volatility
        np.random.seed(42)  # For reproducible tests

        periods = 100
        base_price = 45000.0

        # Generate realistic price movements
        returns = np.random.normal(0.001, 0.02, periods)  # 0.1% mean, 2% volatility
        prices = [base_price]

        for ret in returns:
            prices.append(prices[-1] * (1 + ret))

        # Create OHLCV data with realistic relationships
        data = []
        for i in range(periods):
            price = prices[i]
            # Add some intraday volatility
            volatility = price * 0.01  # 1% intraday range

            open_price = price + np.random.uniform(-volatility / 2, volatility / 2)
            close_price = prices[i + 1] if i < periods - 1 else price

            high_price = max(open_price, close_price) + np.random.uniform(0, volatility / 2)
            low_price = min(open_price, close_price) - np.random.uniform(0, volatility / 2)

            volume = np.random.uniform(100, 1000)

            data.append(
                {
                    "timestamp": 1640995200000 + i * 3600000,  # Hourly timestamps
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": round(volume, 2),
                }
            )

        return pd.DataFrame(data)

    @pytest.fixture
    def minimal_data(self) -> pd.DataFrame:
        """Create minimal test data."""
        return pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000, 1641002400000],
                "open": [46000.0, 46500.0, 47000.0],
                "high": [47000.0, 47500.0, 48000.0],
                "low": [45500.0, 46000.0, 46800.0],
                "close": [46500.0, 47000.0, 47800.0],
                "volume": [100.5, 150.2, 200.1],
            }
        )

    # MovingAverageStrategy Tests
    def test_moving_average_strategy_should_calculate_sma(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test SMA calculation."""
        strategy = MovingAverageStrategy()
        result = strategy.calculate(sample_ohlcv_data)

        assert "sma_20" in result.columns
        assert "sma_50" in result.columns

        # Check that SMA values are calculated correctly
        expected_sma_20 = sample_ohlcv_data["close"].rolling(window=20).mean()
        pd.testing.assert_series_equal(result["sma_20"], expected_sma_20, check_names=False)

    def test_moving_average_strategy_should_calculate_ema(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test EMA calculation."""
        strategy = MovingAverageStrategy()
        result = strategy.calculate(sample_ohlcv_data)

        assert "ema_12" in result.columns
        assert "ema_26" in result.columns

        # Check that EMA values are calculated correctly
        expected_ema_12 = sample_ohlcv_data["close"].ewm(span=12).mean()
        pd.testing.assert_series_equal(result["ema_12"], expected_ema_12, check_names=False)

    def test_moving_average_strategy_should_handle_insufficient_data(
        self, minimal_data: pd.DataFrame
    ) -> None:
        """Test moving averages with insufficient data."""
        strategy = MovingAverageStrategy()
        result = strategy.calculate(minimal_data)

        # Should have columns but mostly NaN values
        assert "sma_20" in result.columns
        assert "sma_50" in result.columns
        assert result["sma_20"].isna().sum() > 0  # Should have NaN values
        assert result["sma_50"].isna().sum() > 0

    # MACDStrategy Tests
    def test_macd_strategy_should_calculate_macd_indicators(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test MACD calculation."""
        strategy = MACDStrategy()
        result = strategy.calculate(sample_ohlcv_data)

        assert "macd" in result.columns
        assert "macd_signal" in result.columns
        assert "macd_histogram" in result.columns

        # Verify MACD calculation logic
        ema_12 = result["ema_12"]
        ema_26 = result["ema_26"]
        expected_macd = ema_12 - ema_26

        pd.testing.assert_series_equal(result["macd"], expected_macd, check_names=False)

    def test_macd_strategy_should_create_emas_if_missing(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test MACD creates EMAs if not present."""
        # Remove EMA columns if they exist
        data_without_ema = sample_ohlcv_data.drop(columns=["ema_12", "ema_26"], errors="ignore")

        strategy = MACDStrategy()
        result = strategy.calculate(data_without_ema)

        assert "ema_12" in result.columns
        assert "ema_26" in result.columns
        assert "macd" in result.columns

    def test_macd_strategy_should_calculate_signal_and_histogram(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test MACD signal and histogram calculation."""
        strategy = MACDStrategy()
        result = strategy.calculate(sample_ohlcv_data)

        # Signal should be EMA of MACD
        expected_signal = result["macd"].ewm(span=9).mean()
        pd.testing.assert_series_equal(result["macd_signal"], expected_signal, check_names=False)

        # Histogram should be MACD - Signal
        expected_histogram = result["macd"] - result["macd_signal"]
        pd.testing.assert_series_equal(
            result["macd_histogram"], expected_histogram, check_names=False
        )

    # RSIStrategy Tests
    def test_rsi_strategy_should_calculate_rsi(self, sample_ohlcv_data: pd.DataFrame) -> None:
        """Test RSI calculation."""
        strategy = RSIStrategy(period=14)
        result = strategy.calculate(sample_ohlcv_data)

        assert "rsi" in result.columns

        # RSI should be between 0 and 100
        rsi_values = result["rsi"].dropna()
        assert (rsi_values >= 0).all()
        assert (rsi_values <= 100).all()

    def test_rsi_strategy_should_handle_custom_period(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test RSI with custom period."""
        strategy = RSIStrategy(period=21)
        result = strategy.calculate(sample_ohlcv_data)

        assert "rsi" in result.columns
        # Should have more NaN values at the beginning due to longer period
        assert (
            result["rsi"].notna().idxmax() >= 20
        )  # First valid RSI should be at index 20 or later

    def test_rsi_strategy_should_handle_no_price_changes(self) -> None:
        """Test RSI with constant prices (no changes)."""
        constant_data = pd.DataFrame(
            {
                "timestamp": [1640995200000 + i * 3600000 for i in range(20)],
                "open": [46000.0] * 20,
                "high": [46000.0] * 20,
                "low": [46000.0] * 20,
                "close": [46000.0] * 20,
                "volume": [100.0] * 20,
            }
        )

        strategy = RSIStrategy(period=14)
        result = strategy.calculate(constant_data)

        # RSI should be 50 when there are no price changes
        rsi_values = result["rsi"].dropna()
        # Due to division by infinity handling, should not crash
        assert not rsi_values.isna().all()

    # BollingerBandsStrategy Tests
    def test_bollinger_bands_strategy_should_calculate_bands(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test Bollinger Bands calculation."""
        strategy = BollingerBandsStrategy(period=20, std_multiplier=2.0)
        result = strategy.calculate(sample_ohlcv_data)

        assert "bb_upper" in result.columns
        assert "bb_lower" in result.columns
        assert "bb_middle" in result.columns

        # Middle band should be SMA
        expected_middle = sample_ohlcv_data["close"].rolling(window=20).mean()
        pd.testing.assert_series_equal(result["bb_middle"], expected_middle, check_names=False)

        # Upper band should be above middle, lower band should be below
        valid_data = result.dropna()
        assert (valid_data["bb_upper"] >= valid_data["bb_middle"]).all()
        assert (valid_data["bb_lower"] <= valid_data["bb_middle"]).all()

    def test_bollinger_bands_strategy_should_handle_custom_parameters(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test Bollinger Bands with custom parameters."""
        strategy = BollingerBandsStrategy(period=10, std_multiplier=1.5)
        result = strategy.calculate(sample_ohlcv_data)

        assert "bb_upper" in result.columns
        assert "bb_lower" in result.columns
        assert "bb_middle" in result.columns

        # Should have fewer NaN values due to shorter period
        assert result["bb_middle"].notna().idxmax() == 9  # First valid value at index 9

    def test_bollinger_bands_strategy_should_calculate_correct_width(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test Bollinger Bands width calculation."""
        strategy = BollingerBandsStrategy(period=20, std_multiplier=2.0)
        result = strategy.calculate(sample_ohlcv_data)

        # Verify the bands are calculated correctly
        middle = result["bb_middle"]
        std = sample_ohlcv_data["close"].rolling(window=20).std()

        expected_upper = middle + (2.0 * std)
        expected_lower = middle - (2.0 * std)

        pd.testing.assert_series_equal(result["bb_upper"], expected_upper, check_names=False)
        pd.testing.assert_series_equal(result["bb_lower"], expected_lower, check_names=False)

    # VWAPStrategy Tests
    def test_vwap_strategy_should_calculate_vwap(self, sample_ohlcv_data: pd.DataFrame) -> None:
        """Test VWAP calculation."""
        strategy = VWAPStrategy()
        result = strategy.calculate(sample_ohlcv_data)

        assert "vwap" in result.columns

        # VWAP should be in a reasonable range compared to prices
        assert result["vwap"].min() >= sample_ohlcv_data["low"].min() * 0.9
        assert result["vwap"].max() <= sample_ohlcv_data["high"].max() * 1.1

    def test_vwap_strategy_should_be_volume_weighted(self, sample_ohlcv_data: pd.DataFrame) -> None:
        """Test VWAP is properly volume weighted."""
        strategy = VWAPStrategy()
        result = strategy.calculate(sample_ohlcv_data)

        # Manual VWAP calculation for verification
        typical_price = (
            sample_ohlcv_data["high"] + sample_ohlcv_data["low"] + sample_ohlcv_data["close"]
        ) / 3
        volume_price = typical_price * sample_ohlcv_data["volume"]
        expected_vwap = volume_price.cumsum() / sample_ohlcv_data["volume"].cumsum()

        pd.testing.assert_series_equal(result["vwap"], expected_vwap, check_names=False)

    def test_vwap_strategy_should_handle_zero_volume(self) -> None:
        """Test VWAP with zero volume periods."""
        data_with_zero_volume = pd.DataFrame(
            {
                "timestamp": [1640995200000, 1640998800000, 1641002400000],
                "open": [46000.0, 46500.0, 47000.0],
                "high": [47000.0, 47500.0, 48000.0],
                "low": [45500.0, 46000.0, 46800.0],
                "close": [46500.0, 47000.0, 47800.0],
                "volume": [100.0, 0.0, 200.0],  # Zero volume in middle
            }
        )

        strategy = VWAPStrategy()
        result = strategy.calculate(data_with_zero_volume)

        # Should handle zero volume without crashing
        assert "vwap" in result.columns
        assert not result["vwap"].isna().all()

    # TechnicalIndicatorsCalculator Tests
    def test_calculator_should_initialize_with_default_strategies(self) -> None:
        """Test calculator initialization with default strategies."""
        calculator = TechnicalIndicatorsCalculator()

        strategies = calculator.get_available_indicators()
        expected_strategies = ["moving_averages", "macd", "rsi", "bollinger_bands", "vwap"]

        for strategy in expected_strategies:
            assert strategy in strategies

    def test_calculator_should_calculate_all_indicators(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test calculating all indicators at once."""
        calculator = TechnicalIndicatorsCalculator()
        result = calculator.calculate_all_indicators(sample_ohlcv_data)

        # Should have all expected indicator columns
        expected_columns = [
            "sma_20",
            "sma_50",
            "ema_12",
            "ema_26",
            "macd",
            "macd_signal",
            "macd_histogram",
            "rsi",
            "bb_upper",
            "bb_lower",
            "bb_middle",
            "vwap",
        ]

        for column in expected_columns:
            assert column in result.columns

        # Original columns should still be present
        for column in sample_ohlcv_data.columns:
            assert column in result.columns

    def test_calculator_should_calculate_specific_indicators(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test calculating only specific indicators."""
        calculator = TechnicalIndicatorsCalculator()
        result = calculator.calculate_specific_indicators(
            sample_ohlcv_data, ["moving_averages", "rsi"]
        )

        # Should have moving averages and RSI
        assert "sma_20" in result.columns
        assert "rsi" in result.columns

        # Should not have MACD or Bollinger Bands
        assert "macd" not in result.columns
        assert "bb_upper" not in result.columns

    def test_calculator_should_handle_unknown_indicators(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test handling of unknown indicator names."""
        calculator = TechnicalIndicatorsCalculator()

        # Should not crash with unknown indicator names
        result = calculator.calculate_specific_indicators(
            sample_ohlcv_data, ["moving_averages", "unknown_indicator"]
        )

        # Should still calculate known indicators
        assert "sma_20" in result.columns

    def test_calculator_should_handle_empty_data(self) -> None:
        """Test calculator with empty DataFrame."""
        calculator = TechnicalIndicatorsCalculator()
        empty_df = pd.DataFrame()

        result = calculator.calculate_all_indicators(empty_df)
        assert result.empty

        result = calculator.calculate_specific_indicators(empty_df, ["moving_averages"])
        assert result.empty

    def test_calculator_should_handle_calculation_errors(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test calculator handles strategy calculation errors gracefully."""
        calculator = TechnicalIndicatorsCalculator()

        # Add a faulty strategy that raises an exception
        from unittest.mock import Mock

        faulty_strategy = Mock()
        faulty_strategy.calculate.side_effect = Exception("Calculation error")
        calculator.add_strategy("faulty", faulty_strategy)

        # Should not crash and return original data
        result = calculator.calculate_all_indicators(sample_ohlcv_data)

        # Should return original data when calculation fails
        assert len(result) == len(sample_ohlcv_data)
        for column in sample_ohlcv_data.columns:
            assert column in result.columns

    def test_calculator_should_allow_custom_strategies(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test adding custom indicator strategies."""
        calculator = TechnicalIndicatorsCalculator()

        # Create custom strategy
        from unittest.mock import Mock

        custom_strategy = Mock()
        custom_strategy.calculate.return_value = sample_ohlcv_data.assign(custom_indicator=100.0)

        calculator.add_strategy("custom", custom_strategy)

        result = calculator.calculate_specific_indicators(sample_ohlcv_data, ["custom"])
        assert "custom_indicator" in result.columns
        assert (result["custom_indicator"] == 100.0).all()

    def test_calculator_should_allow_strategy_removal(self) -> None:
        """Test removing indicator strategies."""
        calculator = TechnicalIndicatorsCalculator()

        # Remove a strategy
        calculator.remove_strategy("rsi")
        strategies = calculator.get_available_indicators()
        assert "rsi" not in strategies

        # Removing non-existent strategy should not crash
        calculator.remove_strategy("non_existent")

    # Factory Function Tests
    def test_create_technical_indicators_calculator_should_return_configured_calculator(
        self,
    ) -> None:
        """Test factory function returns properly configured calculator."""
        calculator = create_technical_indicators_calculator()

        assert isinstance(calculator, TechnicalIndicatorsCalculator)
        strategies = calculator.get_available_indicators()
        assert len(strategies) >= 5  # Should have all default strategies

    def test_calculate_basic_indicators_should_work_as_convenience_function(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test convenience function for calculating basic indicators."""
        result = calculate_basic_indicators(sample_ohlcv_data)

        # Should have all basic indicators
        expected_columns = [
            "sma_20",
            "sma_50",
            "ema_12",
            "ema_26",
            "macd",
            "macd_signal",
            "macd_histogram",
            "rsi",
            "bb_upper",
            "bb_lower",
            "bb_middle",
            "vwap",
        ]

        for column in expected_columns:
            assert column in result.columns

    # Integration and Performance Tests
    def test_indicators_should_work_with_large_dataset(self) -> None:
        """Test indicators with large dataset."""
        # Create large dataset
        large_data = pd.DataFrame(
            {
                "timestamp": [1640995200000 + i * 3600000 for i in range(10000)],
                "open": [46000.0 + np.random.randn() * 100 for _ in range(10000)],
                "high": [47000.0 + np.random.randn() * 100 for _ in range(10000)],
                "low": [45000.0 + np.random.randn() * 100 for _ in range(10000)],
                "close": [46500.0 + np.random.randn() * 100 for _ in range(10000)],
                "volume": [100.0 + np.random.randn() * 50 for _ in range(10000)],
            }
        )

        calculator = TechnicalIndicatorsCalculator()
        result = calculator.calculate_all_indicators(large_data)

        assert len(result) == len(large_data)
        assert "sma_20" in result.columns
        assert "rsi" in result.columns

    def test_indicators_should_be_consistent_across_calls(
        self, sample_ohlcv_data: pd.DataFrame
    ) -> None:
        """Test that indicators produce consistent results across multiple calls."""
        calculator = TechnicalIndicatorsCalculator()

        result1 = calculator.calculate_all_indicators(sample_ohlcv_data)
        result2 = calculator.calculate_all_indicators(sample_ohlcv_data)

        # Results should be identical
        pd.testing.assert_frame_equal(result1, result2)

    def test_strategies_should_not_modify_input_data(self, sample_ohlcv_data: pd.DataFrame) -> None:
        """Test that strategies don't modify input data."""
        original_data = sample_ohlcv_data.copy()

        strategy = MovingAverageStrategy()
        strategy.calculate(sample_ohlcv_data)

        # Original data should be unchanged
        pd.testing.assert_frame_equal(sample_ohlcv_data, original_data)
