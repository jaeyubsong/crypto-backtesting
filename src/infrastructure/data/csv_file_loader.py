"""
CSV File Loading utilities.

This module provides efficient loading of individual CSV files
with validation and error handling.
"""

import asyncio
from pathlib import Path

import pandas as pd
from loguru import logger

from src.core.exceptions.backtest import DataError

from .csv_cache_core import CSVCacheCore
from .csv_validator import CSVValidator


class CSVFileLoader:
    """Handles loading and validation of individual CSV files."""

    def __init__(self, cache_core: CSVCacheCore):
        """Initialize the file loader with cache core."""
        self.cache_core = cache_core

    async def load_single_file(self, file_path: Path) -> pd.DataFrame:
        """Load a single CSV file with caching."""
        cache_key = self.cache_core._build_cache_key(file_path)

        # Check cache first
        cached_result = self.cache_core._check_cache_hit(cache_key, {"file_path": str(file_path)})
        if cached_result is not None:
            return cached_result

        # Load from disk if not cached
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        try:
            logger.debug(f"Loading file: {file_path}")
            df = await self._load_csv_from_disk(file_path)
            return self._validate_and_cache_result(df, cache_key, file_path)

        except pd.errors.EmptyDataError:
            return self._handle_empty_file()
        except OSError as e:
            logger.error(f"File system error loading {file_path.name}: {str(e)}")
            raise DataError(f"File system error loading {file_path.name}") from e
        except (pd.errors.ParserError, ValueError, TypeError) as e:
            # Handle specific CSV parsing errors
            logger.error(f"CSV parsing error ({type(e).__name__}) in {file_path.name}: {str(e)}")
            return self._handle_loading_error(e, file_path)
        except (UnicodeDecodeError, MemoryError) as e:
            # Handle encoding and memory issues
            logger.error(
                f"Encoding or memory error ({type(e).__name__}) loading {file_path.name}: {str(e)}"
            )
            return self._handle_loading_error(e, file_path)
        except Exception as e:
            # Only catch truly unexpected exceptions
            error_msg = (
                str(e).replace("{", "{{").replace("}", "}}")
            )  # Escape braces for safe logging
            logger.error(
                f"Unexpected error ({type(e).__name__}) loading {file_path.name}: {error_msg}",
                exc_info=True,
            )
            return self._handle_loading_error(e, file_path)

    async def _load_csv_from_disk(self, file_path: Path) -> pd.DataFrame:
        """Load CSV file from disk using async executor with proper resource management."""
        loop = asyncio.get_event_loop()

        def _read_csv_safely() -> pd.DataFrame:
            """Read CSV with proper file handle management."""
            try:
                return pd.read_csv(
                    file_path,
                    dtype={
                        "timestamp": "int64",
                        "open": "float64",
                        "high": "float64",
                        "low": "float64",
                        "close": "float64",
                        "volume": "float64",
                    },
                )
            except Exception as e:
                # Ensure any file handles are properly cleaned up
                logger.debug(f"CSV read failed for {file_path.name}: {str(e)}")
                raise

        return await loop.run_in_executor(None, _read_csv_safely)

    def _validate_and_cache_result(
        self, df: pd.DataFrame, cache_key: str, file_path: Path
    ) -> pd.DataFrame:
        """Validate DataFrame and cache the result with memory tracking."""
        CSVValidator.validate_csv_structure(df, file_path)

        return self.cache_core._validate_and_cache_result(
            df, cache_key, {"file_path": str(file_path), "file_name": file_path.name}
        )

    def _handle_empty_file(self) -> pd.DataFrame:
        """Handle empty CSV files gracefully."""
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    def _handle_loading_error(self, error: Exception, file_path: Path) -> pd.DataFrame:
        """Handle CSV loading errors with proper sanitization."""
        logger.error(f"CSV file loading failed: {file_path.name}", exc_info=True)
        raise DataError(f"Failed to load CSV file: {file_path.name}") from error


class CSVCache(CSVCacheCore):
    """
    Combined CSV cache with file loading capabilities.

    This class maintains backward compatibility while leveraging
    the new modular architecture.
    """

    def __init__(
        self, cache_size: int = CSVCacheCore.DEFAULT_CACHE_SIZE, enable_observers: bool = True
    ):
        """Initialize the CSV cache with file loading capabilities."""
        super().__init__(cache_size, enable_observers)
        self.file_loader = CSVFileLoader(self)

    async def load_single_file(self, file_path: Path) -> pd.DataFrame:
        """Load a single CSV file with caching."""
        return await self.file_loader.load_single_file(file_path)
