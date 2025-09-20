"""
Technical Indicators Calculator.

This module provides calculation of various technical indicators for financial data analysis.
Implements the Strategy Pattern for different indicator calculation strategies.
"""

from typing import Protocol

import pandas as pd
from loguru import logger

from src.core.exceptions.backtest import DataError


class IndicatorStrategy(Protocol):
    """Protocol for technical indicator calculation strategies."""

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate specific indicator for the given data."""
        ...


class MovingAverageStrategy:
    """Strategy for calculating moving averages (SMA and EMA)."""

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add simple and exponential moving averages."""
        result = data.copy()

        # Simple moving averages
        result["sma_20"] = result["close"].rolling(window=20).mean()
        result["sma_50"] = result["close"].rolling(window=50).mean()

        # Exponential moving averages
        result["ema_12"] = result["close"].ewm(span=12).mean()
        result["ema_26"] = result["close"].ewm(span=26).mean()

        return result


class MACDStrategy:
    """Strategy for calculating MACD (Moving Average Convergence Divergence) indicators."""

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add MACD indicators (requires EMA columns to be present)."""
        result = data.copy()

        # Ensure EMA columns exist
        if "ema_12" not in result.columns or "ema_26" not in result.columns:
            # Calculate EMAs if not present
            result["ema_12"] = result["close"].ewm(span=12).mean()
            result["ema_26"] = result["close"].ewm(span=26).mean()

        result["macd"] = result["ema_12"] - result["ema_26"]
        result["macd_signal"] = result["macd"].ewm(span=9).mean()
        result["macd_histogram"] = result["macd"] - result["macd_signal"]

        return result


class RSIStrategy:
    """Strategy for calculating RSI (Relative Strength Index) indicator."""

    def __init__(self, period: int = 14):
        """Initialize RSI strategy with configurable period."""
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add RSI indicator."""
        result = data.copy()

        delta = result["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=self.period).mean()
        loss = (-delta).where(delta < 0, 0).rolling(window=self.period).mean()

        # Avoid division by zero
        rs = gain / loss.replace(0, float("inf"))
        result["rsi"] = 100 - (100 / (1 + rs))

        return result


class BollingerBandsStrategy:
    """Strategy for calculating Bollinger Bands indicators."""

    def __init__(self, period: int = 20, std_multiplier: float = 2.0):
        """Initialize Bollinger Bands strategy with configurable parameters."""
        self.period = period
        self.std_multiplier = std_multiplier

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add Bollinger Bands indicators."""
        result = data.copy()

        bb_middle = result["close"].rolling(window=self.period).mean()
        bb_std = result["close"].rolling(window=self.period).std()

        result["bb_upper"] = bb_middle + (self.std_multiplier * bb_std)
        result["bb_lower"] = bb_middle - (self.std_multiplier * bb_std)
        result["bb_middle"] = bb_middle

        return result


class VWAPStrategy:
    """Strategy for calculating VWAP (Volume Weighted Average Price) indicator."""

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add VWAP indicator."""
        result = data.copy()

        # Typical price calculation
        typical_price = (result["high"] + result["low"] + result["close"]) / 3

        # VWAP calculation
        result["vwap"] = (typical_price * result["volume"]).cumsum() / result["volume"].cumsum()

        return result


class TechnicalIndicatorsCalculator:
    """
    Technical indicators calculator using Strategy Pattern.

    This class orchestrates different indicator calculation strategies
    and provides a clean interface for adding indicators to OHLCV data.
    """

    def __init__(self) -> None:
        """Initialize calculator with default strategies."""
        self._strategies: dict[str, IndicatorStrategy] = {
            "moving_averages": MovingAverageStrategy(),
            "macd": MACDStrategy(),
            "rsi": RSIStrategy(),
            "bollinger_bands": BollingerBandsStrategy(),
            "vwap": VWAPStrategy(),
        }
        self._failure_counts: dict[str, int] = {}

    def add_strategy(self, name: str, strategy: IndicatorStrategy) -> None:
        """Add a new indicator calculation strategy."""
        self._strategies[name] = strategy

    def remove_strategy(self, name: str) -> None:
        """Remove an indicator calculation strategy."""
        self._strategies.pop(name, None)

    def calculate_all_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all configured technical indicators.

        Args:
            data: OHLCV DataFrame

        Returns:
            DataFrame with additional indicator columns
        """
        if data.empty:
            return data

        try:
            result = data.copy()

            # Apply all strategies in sequence
            for name, strategy in self._strategies.items():
                logger.debug(f"Calculating {name} indicators")
                try:
                    result = strategy.calculate(result)
                except (ValueError, TypeError, KeyError) as strategy_error:
                    self._failure_counts[name] = self._failure_counts.get(name, 0) + 1
                    logger.warning(
                        f"Failed {name} (failure #{self._failure_counts[name]}): {strategy_error}"
                    )
                    # Continue with other indicators instead of failing completely
                    continue
                except Exception as unexpected_error:
                    logger.error(
                        f"Unexpected error calculating {name} indicator: {unexpected_error}"
                    )
                    raise DataError(
                        f"Technical indicator calculation failed for {name}"
                    ) from unexpected_error

            logger.info(f"Calculated all technical indicators for {len(result)} rows")
            return result

        except DataError:
            # Re-raise DataError as is
            raise
        except Exception as e:
            logger.error(f"Failed to calculate indicators: {str(e)}")
            raise DataError(f"Technical indicators calculation failed: {str(e)}") from e

    def calculate_specific_indicators(
        self, data: pd.DataFrame, indicator_names: list[str]
    ) -> pd.DataFrame:
        """
        Calculate only specific technical indicators.

        Args:
            data: OHLCV DataFrame
            indicator_names: List of indicator strategy names to calculate

        Returns:
            DataFrame with specified indicator columns
        """
        if data.empty:
            return data

        try:
            result = data.copy()

            # Apply only requested strategies
            for name in indicator_names:
                if name in self._strategies:
                    logger.debug(f"Calculating {name} indicators")
                    result = self._strategies[name].calculate(result)
                else:
                    logger.warning(f"Unknown indicator strategy: {name}")

            logger.info(f"Calculated {indicator_names} indicators for {len(result)} rows")
            return result

        except Exception as e:
            logger.error(f"Failed to calculate specific indicators: {str(e)}")
            raise DataError(f"Specific technical indicators calculation failed: {str(e)}") from e

    def get_available_indicators(self) -> list[str]:
        """Get list of available indicator strategies."""
        return list(self._strategies.keys())

    def get_failure_statistics(self) -> dict[str, int]:
        """Get failure counts for each indicator strategy."""
        return self._failure_counts.copy()

    def reset_failure_statistics(self) -> None:
        """Reset failure counts for monitoring purposes."""
        self._failure_counts.clear()


# Factory function for easy instantiation
def create_technical_indicators_calculator() -> TechnicalIndicatorsCalculator:
    """Factory function to create a technical indicators calculator with default strategies."""
    return TechnicalIndicatorsCalculator()


# Convenience functions for backward compatibility
def calculate_basic_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate basic technical indicators (backward compatibility function)."""
    calculator = create_technical_indicators_calculator()
    return calculator.calculate_all_indicators(data)
