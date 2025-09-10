#!/usr/bin/env python3
"""
Binance Data Downloader

Downloads historical futures trade data from Binance Data Vision and optionally
converts it to OHLCV format using the existing conversion script.

URL Pattern: https://data.binance.vision/data/futures/um/daily/trades/{SYMBOL}/{SYMBOL}-trades-{YYYY-MM-DD}.zip
"""

import argparse
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import requests
from loguru import logger
from tqdm import tqdm


class BinanceDataDownloader:
    """Downloads and processes Binance futures trade data."""

    BASE_URL = "https://data.binance.vision/data/futures/um/daily/trades"

    def __init__(self, raw_data_dir: str = "data/raw/binance"):
        self.raw_data_dir = Path(raw_data_dir)
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        )

    def generate_date_range(self, start_date: str, end_date: str) -> list[str]:
        """Generate list of dates between start and end date (inclusive)."""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        return dates

    def build_download_url(self, symbol: str, date: str) -> str:
        """Build download URL for specific symbol and date."""
        return f"{self.BASE_URL}/{symbol}/{symbol}-trades-{date}.zip"

    def download_file(self, url: str, output_path: Path, max_retries: int = 3) -> bool:
        """Download a single file with retry logic."""
        for attempt in range(max_retries):
            try:
                logger.info(f"Downloading {url} (attempt {attempt + 1}/{max_retries})")

                response = self.session.get(url, stream=True)
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))

                with (
                    open(output_path, "wb") as f,
                    tqdm(
                        total=total_size,
                        unit="B",
                        unit_scale=True,
                        desc=f"Downloading {output_path.name}",
                    ) as pbar,
                ):
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

                logger.success(f"Downloaded {output_path.name} ({total_size:,} bytes)")
                return True

            except requests.exceptions.RequestException as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to download {url} after {max_retries} attempts")
                    return False

        return False

    def extract_zip_file(self, zip_path: Path, extract_to: Path) -> bool:
        """Extract ZIP file and remove the ZIP after extraction."""
        try:
            logger.info(f"Extracting {zip_path.name}")

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_to)

            # Remove the ZIP file after extraction
            zip_path.unlink()
            logger.success(f"Extracted and cleaned up {zip_path.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to extract {zip_path}: {e}")
            return False

    def download_symbol_range(
        self, symbol: str, start_date: str, end_date: str, max_retries: int = 3
    ) -> list[str]:
        """Download data for a symbol over a date range."""
        dates = self.generate_date_range(start_date, end_date)
        downloaded_files = []

        logger.info(
            f"Downloading {symbol} data from {start_date} to {end_date} ({len(dates)} days)"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            for date in dates:
                url = self.build_download_url(symbol, date)
                zip_filename = f"{symbol}-trades-{date}.zip"
                zip_path = temp_path / zip_filename

                # Download ZIP file
                if self.download_file(url, zip_path, max_retries):
                    # Extract to raw data directory
                    if self.extract_zip_file(zip_path, self.raw_data_dir):
                        csv_filename = f"{symbol}-trades-{date}.csv"
                        downloaded_files.append(csv_filename)
                else:
                    logger.warning(f"Skipping {date} due to download failure")

        logger.success(f"Downloaded {len(downloaded_files)} files for {symbol}")
        return downloaded_files

    def run_conversion_script(self, timeframes: list[str]) -> bool:
        """Run the existing OHLCV conversion script."""
        try:
            logger.info(f"Converting downloaded data to OHLCV format: {timeframes}")

            cmd = [
                "uv",
                "run",
                "python",
                "scripts/convert_trades_to_ohlcv.py",
                "--timeframes",
                *timeframes,
                "--raw-dir",
                str(self.raw_data_dir),
                "--output-dir",
                "data/binance/futures",  # Use futures directory with daily structure
            ]

            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.success("OHLCV conversion completed successfully")
            logger.info(result.stdout)
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Conversion script failed: {e}")
            logger.error(f"Error output: {e.stderr}")
            return False


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
        description="Download Binance futures trade data and optionally convert to OHLCV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download single day
  python download_binance_data.py --symbol BTCUSDT --start-date 2025-01-01 --end-date 2025-01-01

  # Download range and convert
  python download_binance_data.py --symbol BTCUSDT --start-date 2025-01-01 --end-date 2025-01-03 --convert --timeframes 1m 5m 1h

  # Download multiple days without conversion
  python download_binance_data.py --symbol ETHUSDT --start-date 2024-12-01 --end-date 2024-12-31
        """,
    )

    parser.add_argument(
        "--symbol", type=str, required=True, help="Trading symbol (e.g., BTCUSDT, ETHUSDT)"
    )

    parser.add_argument(
        "--start-date", type=str, required=True, help="Start date in YYYY-MM-DD format"
    )

    parser.add_argument("--end-date", type=str, required=True, help="End date in YYYY-MM-DD format")

    parser.add_argument(
        "--convert",
        action="store_true",
        help="Automatically convert downloaded data to OHLCV format",
    )

    parser.add_argument(
        "--timeframes",
        nargs="+",
        choices=["1m", "5m", "15m", "1h", "4h", "1d"],
        default=["1m", "5m", "1h"],
        help="Timeframes for OHLCV conversion (default: 1m 5m 1h)",
    )

    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw/binance",
        help="Directory to store raw trade files (default: data/raw/binance)",
    )

    parser.add_argument(
        "--max-retries", type=int, default=3, help="Maximum download retries per file (default: 3)"
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Validate date format
    try:
        datetime.strptime(args.start_date, "%Y-%m-%d")
        datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError:
        logger.error("Invalid date format. Use YYYY-MM-DD format.")
        return 1

    # Validate date range
    if args.start_date > args.end_date:
        logger.error("Start date must be before or equal to end date")
        return 1

    setup_logging(args.debug)

    downloader = BinanceDataDownloader(args.raw_dir)

    try:
        # Download data
        downloaded_files = downloader.download_symbol_range(
            args.symbol, args.start_date, args.end_date, args.max_retries
        )

        if not downloaded_files:
            logger.error("No files were successfully downloaded")
            return 1

        # Convert if requested
        if args.convert:
            success = downloader.run_conversion_script(args.timeframes)
            if not success:
                logger.error("Conversion failed")
                return 1

        logger.success(f"Pipeline completed successfully! Downloaded {len(downloaded_files)} files")
        return 0

    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
