"""
OHLCV data summary generation module.

Provides comprehensive summary statistics for OHLCV market data.
"""

from typing import Any

import pandas as pd


class OHLCVSummaryGenerator:
    """
    OHLCV data summary generator with comprehensive statistics.

    Features:
    - Time range statistics
    - Price statistics (min, max, changes)
    - Volume statistics
    - Data quality metrics
    """

    def get_data_summary(self, data: pd.DataFrame) -> dict[str, Any]:
        """
        Get summary statistics for OHLCV data.

        Args:
            data: OHLCV DataFrame

        Returns:
            Dictionary with summary statistics
        """
        if data.empty:
            return {"status": "empty", "rows": 0}

        try:
            summary = {
                "status": "valid",
                "rows": len(data),
            }

            # Add time information
            summary.update(self._get_time_statistics(data))

            # Add price statistics
            summary["price_stats"] = self._get_price_statistics(data)

            # Add data quality metrics
            summary["data_quality"] = self._get_data_quality_metrics(data)

            return summary

        except Exception as e:
            return {"status": "error", "error": str(e), "rows": len(data)}

    def _get_time_statistics(self, data: pd.DataFrame) -> dict[str, str]:
        """Extract time-related statistics from data."""
        return {
            "start_time": pd.to_datetime(
                data["timestamp"].iloc[0], unit="ms", utc=True
            ).isoformat(),
            "end_time": pd.to_datetime(data["timestamp"].iloc[-1], unit="ms", utc=True).isoformat(),
        }

    def _get_price_statistics(self, data: pd.DataFrame) -> dict[str, float]:
        """Calculate comprehensive price statistics."""
        price_stats = {
            "min_low": float(data["low"].min()),
            "max_high": float(data["high"].max()),
            "first_open": float(data["open"].iloc[0]),
            "last_close": float(data["close"].iloc[-1]),
            "total_volume": float(data["volume"].sum()),
            "avg_volume": float(data["volume"].mean()),
        }

        # Add price change calculations
        if len(data) > 0:
            price_change = data["close"].iloc[-1] - data["open"].iloc[0]
            price_change_pct = (price_change / data["open"].iloc[0]) * 100
            price_stats["total_change"] = float(price_change)
            price_stats["total_change_pct"] = float(price_change_pct)

        return price_stats

    def _get_data_quality_metrics(self, data: pd.DataFrame) -> dict[str, int]:
        """Calculate data quality metrics."""
        return {
            "missing_values": int(data.isna().sum().sum()),
            "duplicate_timestamps": int(data["timestamp"].duplicated().sum()),
            "zero_volume_periods": int((data["volume"] == 0).sum()),
        }
