#!/usr/bin/env python3
"""
Data Conversion Script: Binance Trades to OHLCV

Converts raw Binance trade data to OHLCV format required by the backtesting platform.
Input: CSV files with columns: id,price,qty,quote_qty,time,is_buyer_maker
Output: CSV files with columns: timestamp,open,high,low,close,volume
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from loguru import logger


class TradeToOHLCVConverter:
    """Converts individual trade records to OHLCV candles."""

    TIMEFRAME_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}

    def __init__(
        self, raw_data_dir: str = "data/raw/binance", output_dir: str = "data/binance/spot"
    ):
        self.raw_data_dir = Path(raw_data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def convert_file(self, file_path: Path, timeframes: list[str]) -> dict[str, str]:
        """
        Convert a single trade file to OHLCV format for specified timeframes.

        Args:
            file_path: Path to the raw trade CSV file
            timeframes: List of timeframe strings (e.g., ['1m', '5m', '1h'])

        Returns:
            Dict mapping timeframe to output file path
        """
        symbol = self._extract_symbol_from_filename(file_path.name)
        logger.info(f"Converting {file_path.name} for symbol {symbol}")

        # Read trades data
        trades_df = self._read_trades_file(file_path)
        logger.info(f"Loaded {len(trades_df)} trades")

        output_files = {}

        for timeframe in timeframes:
            logger.info(f"Processing {timeframe} timeframe")
            ohlcv_df = self._aggregate_to_ohlcv(trades_df, timeframe)

            output_file = self.output_dir / f"{symbol}_{timeframe}.csv"
            self._save_ohlcv(ohlcv_df, output_file)
            output_files[timeframe] = str(output_file)

            logger.success(f"Created {output_file} with {len(ohlcv_df)} candles")

        return output_files

    def _extract_symbol_from_filename(self, filename: str) -> str:
        """Extract trading symbol from filename like 'BTCUSDT-trades-2025-09-08.csv'"""
        return filename.split("-")[0]

    def _read_trades_file(self, file_path: Path) -> pd.DataFrame:
        """Read and validate trades CSV file."""
        try:
            df = pd.read_csv(file_path)

            # Validate required columns
            required_columns = ["id", "price", "qty", "quote_qty", "time", "is_buyer_maker"]
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")

            # Convert data types
            df["price"] = pd.to_numeric(df["price"])
            df["qty"] = pd.to_numeric(df["qty"])
            df["time"] = pd.to_numeric(df["time"])

            # Convert timestamp to datetime
            df["datetime"] = pd.to_datetime(df["time"], unit="ms")

            # Sort by timestamp
            df = df.sort_values("time").reset_index(drop=True)

            return df

        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            raise

    def _aggregate_to_ohlcv(self, trades_df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Aggregate individual trades into OHLCV candles."""
        interval_seconds = self.TIMEFRAME_SECONDS[timeframe]

        # Create time bins
        trades_df["time_bin"] = (trades_df["time"] // (interval_seconds * 1000)) * (
            interval_seconds * 1000
        )

        # Group by time bin and aggregate
        ohlcv_data = []

        for timestamp, group in trades_df.groupby("time_bin"):
            prices = group["price"]
            volumes = group["qty"]

            ohlc_record = {
                "timestamp": int(timestamp),
                "open": float(prices.iloc[0]),
                "high": float(prices.max()),
                "low": float(prices.min()),
                "close": float(prices.iloc[-1]),
                "volume": float(volumes.sum()),
            }
            ohlcv_data.append(ohlc_record)

        ohlcv_df = pd.DataFrame(ohlcv_data)
        return ohlcv_df.sort_values("timestamp").reset_index(drop=True)

    def _save_ohlcv(self, ohlcv_df: pd.DataFrame, output_file: Path):
        """Save OHLCV data to CSV file."""
        ohlcv_df.to_csv(output_file, index=False)

    def convert_all_files(self, timeframes: list[str]) -> dict[str, dict[str, str]]:
        """Convert all trade files in the raw data directory."""
        trade_files = list(self.raw_data_dir.glob("*-trades-*.csv"))

        if not trade_files:
            logger.warning(f"No trade files found in {self.raw_data_dir}")
            return {}

        results = {}

        for file_path in trade_files:
            try:
                symbol = self._extract_symbol_from_filename(file_path.name)
                results[symbol] = self.convert_file(file_path, timeframes)
            except Exception as e:
                logger.error(f"Failed to convert {file_path}: {e}")
                continue

        return results


def setup_logging(debug: bool = False):
    """Configure logging with loguru."""
    logger.remove()

    level = "DEBUG" if debug else "INFO"
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Convert Binance trade data to OHLCV format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python convert_trades_to_ohlcv.py --timeframes 1m 5m 1h
  python convert_trades_to_ohlcv.py --file BTCUSDT-trades-2025-09-08.csv --timeframes 1m
  python convert_trades_to_ohlcv.py --raw-dir data/raw/binance --output-dir data/binance/spot
        """,
    )

    parser.add_argument(
        "--timeframes",
        nargs="+",
        choices=list(TradeToOHLCVConverter.TIMEFRAME_SECONDS.keys()),
        default=["1m", "5m", "1h"],
        help="Timeframes to generate (default: 1m 5m 1h)",
    )

    parser.add_argument(
        "--file", type=str, help="Specific file to convert (if not provided, converts all files)"
    )

    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw/binance",
        help="Directory containing raw trade files (default: data/raw/binance)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/binance/spot",
        help="Output directory for OHLCV files (default: data/binance/spot)",
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    setup_logging(args.debug)

    converter = TradeToOHLCVConverter(args.raw_dir, args.output_dir)

    try:
        if args.file:
            # Convert specific file
            file_path = Path(args.raw_dir) / args.file
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return 1

            results = converter.convert_file(file_path, args.timeframes)
            logger.success(f"Converted {args.file} to {len(results)} timeframes")
        else:
            # Convert all files
            results = converter.convert_all_files(args.timeframes)
            total_files = sum(len(timeframes) for timeframes in results.values())
            logger.success(f"Converted {len(results)} symbols to {total_files} total files")

        return 0

    except Exception as e:
        logger.exception(f"Conversion failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
