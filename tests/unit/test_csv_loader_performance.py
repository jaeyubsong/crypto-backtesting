"""
Performance and concurrency tests for CSV data loader.

Tests cover performance benchmarks, chunked processing,
concurrent loading, and large dataset handling.
"""

import asyncio
import shutil
import tempfile
import time
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.infrastructure.data.csv_loader import CSVDataLoader


class TestCSVDataLoaderPerformance:
    """Performance and concurrency test suite for CSVDataLoader."""

    @pytest.fixture
    def temp_data_dir(self) -> Generator[Path]:
        """Create temporary data directory."""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            yield temp_dir

        finally:
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def loader(self, temp_data_dir: Path) -> CSVDataLoader:
        """Create CSVDataLoader instance with test data directory."""
        # Create binance directory structure for CSVDataLoader validation
        binance_dir = temp_data_dir / "binance"
        binance_dir.mkdir(parents=True, exist_ok=True)
        return CSVDataLoader(data_directory=str(temp_data_dir), cache_size=10)

    @pytest.mark.asyncio
    async def test_should_handle_concurrent_loading(
        self, loader: CSVDataLoader, temp_data_dir: Path
    ) -> None:
        """Test concurrent data loading."""
        # Create test data
        binance_dir = temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h"
        binance_dir.mkdir(parents=True)

        # Create sample file
        file_path = binance_dir / "BTCUSDT_1h_2025-01-01.csv"
        base_timestamp = int(datetime(2025, 1, 1).timestamp() * 1000)

        df = pd.DataFrame(
            {
                "timestamp": [base_timestamp + h * 3600 * 1000 for h in range(24)],
                "open": [50000 + h * 10 for h in range(24)],
                "high": [50050 + h * 10 for h in range(24)],
                "low": [49950 + h * 10 for h in range(24)],
                "close": [50020 + h * 10 for h in range(24)],
                "volume": [100 + h * 5 for h in range(24)],
            }
        )
        df.to_csv(file_path, index=False)

        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 1, 23, 59, 59)

        # Load same data concurrently
        tasks = []
        for _ in range(5):
            task = loader.load_data("BTCUSDT", "1h", start_date, end_date)
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # All results should be identical
        for result in results[1:]:
            pd.testing.assert_frame_equal(results[0], result)

    @pytest.mark.asyncio
    async def test_should_perform_efficiently_with_large_date_range(
        self, loader: CSVDataLoader, temp_data_dir: Path
    ) -> None:
        """Test performance with larger date ranges."""
        # Create additional test files for performance test
        binance_dir = temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h"
        binance_dir.mkdir(parents=True)

        # Add 13 days of data
        base_date = datetime(2025, 1, 1)
        for i in range(13):
            date = base_date + timedelta(days=i)
            file_path = binance_dir / f"BTCUSDT_1h_{date.strftime('%Y-%m-%d')}.csv"

            # Minimal data for performance
            df = pd.DataFrame(
                {
                    "timestamp": [int((date.timestamp() + h * 3600) * 1000) for h in range(24)],
                    "open": [50000] * 24,
                    "high": [50100] * 24,
                    "low": [49900] * 24,
                    "close": [50000] * 24,
                    "volume": [100] * 24,
                }
            )
            df.to_csv(file_path, index=False)

        # Load large date range
        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 13, 23, 59, 59)  # Include full last day

        start_time = time.time()
        data = await loader.load_data("BTCUSDT", "1h", start_date, end_date)
        load_time = time.time() - start_time

        assert len(data) == 24 * 13  # 13 days of data
        assert load_time < 5.0  # Should load in under 5 seconds

    async def test_should_use_chunked_processing_for_large_datasets(
        self, temp_data_dir: Path
    ) -> None:
        """Test chunked processing is triggered for large datasets."""
        # Create binance directory structure for CSVDataLoader validation
        binance_dir = temp_data_dir / "binance"
        binance_dir.mkdir(parents=True, exist_ok=True)

        loader = CSVDataLoader(str(temp_data_dir))

        # Create binance directory structure
        binance_dir = temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h"
        binance_dir.mkdir(parents=True, exist_ok=True)

        # Create 35 files to trigger chunked processing (threshold is 30)
        base_date = datetime(2025, 1, 1)
        for i in range(35):
            date = base_date + timedelta(days=i)
            file_path = binance_dir / f"BTCUSDT_1h_{date.strftime('%Y-%m-%d')}.csv"

            df = pd.DataFrame(
                {
                    "timestamp": [int((date.timestamp() + h * 3600) * 1000) for h in range(4)],
                    "open": [50000] * 4,
                    "high": [50100] * 4,
                    "low": [49900] * 4,
                    "close": [50000] * 4,
                    "volume": [100] * 4,
                }
            )
            df.to_csv(file_path, index=False)

        # Load large date range to trigger chunked processing
        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 2, 4, 23, 59, 59)

        data = await loader.load_data("BTCUSDT", "1h", start_date, end_date)

        # Verify data was loaded correctly through chunked processing
        assert len(data) > 0
        assert data["timestamp"].is_monotonic_increasing

    async def test_should_handle_chunked_processing_with_missing_files(
        self, temp_data_dir: Path
    ) -> None:
        """Test chunked processing handles missing files gracefully."""
        # Create binance directory structure for CSVDataLoader validation
        binance_dir = temp_data_dir / "binance"
        binance_dir.mkdir(parents=True, exist_ok=True)

        loader = CSVDataLoader(str(temp_data_dir))

        # Create binance directory structure
        binance_dir = temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h"
        binance_dir.mkdir(parents=True, exist_ok=True)

        # Create only some files to trigger chunked processing with missing files
        base_date = datetime(2025, 1, 1)
        created_files = [0, 2, 4, 10, 15, 20, 25, 30, 35, 40]  # Sparse file creation

        for i in created_files:
            date = base_date + timedelta(days=i)
            file_path = binance_dir / f"BTCUSDT_1h_{date.strftime('%Y-%m-%d')}.csv"

            df = pd.DataFrame(
                {
                    "timestamp": [int((date.timestamp() + h * 3600) * 1000) for h in range(2)],
                    "open": [50000] * 2,
                    "high": [50100] * 2,
                    "low": [49900] * 2,
                    "close": [50000] * 2,
                    "volume": [100] * 2,
                }
            )
            df.to_csv(file_path, index=False)

        # Load large date range to trigger chunked processing with missing files
        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 2, 15, 23, 59, 59)

        data = await loader.load_data("BTCUSDT", "1h", start_date, end_date)

        # Should still load available data
        assert len(data) > 0
        # Data should include rows from created files (some may span date range boundaries)
        assert len(data) >= len(created_files) * 2  # At least 2 rows per created file

    async def test_should_be_thread_safe_for_concurrent_cache_access(
        self, temp_data_dir: Path
    ) -> None:
        """Test thread safety of cache operations."""
        # Create binance directory structure for CSVDataLoader validation
        binance_dir = temp_data_dir / "binance"
        binance_dir.mkdir(parents=True, exist_ok=True)

        loader = CSVDataLoader(str(temp_data_dir))

        # Create test data
        binance_dir = temp_data_dir / "binance" / "futures" / "BTCUSDT" / "1h"
        binance_dir.mkdir(parents=True, exist_ok=True)

        file_path = binance_dir / "BTCUSDT_1h_2025-01-01.csv"
        df = pd.DataFrame(
            {
                "timestamp": [1735689600000],
                "open": [50000],
                "high": [50100],
                "low": [49900],
                "close": [50000],
                "volume": [100],
            }
        )
        df.to_csv(file_path, index=False)

        # Test concurrent access
        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 1, 23, 59, 59)

        async def load_data_task() -> pd.DataFrame:
            return await loader.load_data("BTCUSDT", "1h", start_date, end_date)

        # Run multiple concurrent operations
        tasks = [load_data_task() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed and return same data
        assert all(len(result) == 1 for result in results)
        assert all(result.iloc[0]["open"] == 50000 for result in results)
