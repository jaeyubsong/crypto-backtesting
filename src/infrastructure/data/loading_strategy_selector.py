"""
Loading Strategy Selector for automatic strategy selection.

This module provides intelligent strategy selection based on dataset characteristics
and user preferences, implementing the Strategy Pattern for data loading.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from .loading_strategies import (
    ChunkedLoadingStrategy,
    DataLoadingStrategy,
    StandardLoadingStrategy,
    StreamingLoadingStrategy,
)

if TYPE_CHECKING:
    pass


class LoadingStrategySelector:
    """
    Strategy selector that chooses the appropriate loading strategy
    based on dataset characteristics and user preferences.
    """

    def __init__(
        self,
        chunk_threshold: int = 30,
        streaming_threshold: int = 100,
        default_chunk_size: int = 10,
    ):
        """
        Initialize strategy selector with configurable thresholds.

        Args:
            chunk_threshold: File count above which to use chunked strategy
            streaming_threshold: File count above which to use streaming strategy
            default_chunk_size: Default chunk size for chunked strategy
        """
        self.chunk_threshold = chunk_threshold
        self.streaming_threshold = streaming_threshold
        self.default_chunk_size = default_chunk_size

        # Initialize available strategies
        self._strategies = {
            "standard": StandardLoadingStrategy(),
            "chunked": ChunkedLoadingStrategy(chunk_size=default_chunk_size),
            "streaming": StreamingLoadingStrategy(),
        }

        logger.debug(
            f"LoadingStrategySelector initialized: "
            f"chunk_threshold={chunk_threshold}, "
            f"streaming_threshold={streaming_threshold}, "
            f"default_chunk_size={default_chunk_size}"
        )

    def select_strategy(
        self, file_paths: list[Path], strategy_hint: str | None = None
    ) -> DataLoadingStrategy:
        """
        Select appropriate loading strategy based on file count and optional hint.

        Args:
            file_paths: List of file paths to load
            strategy_hint: Optional explicit strategy name ("standard", "chunked", "streaming")

        Returns:
            Selected DataLoadingStrategy instance

        Raises:
            ValueError: If strategy_hint is invalid
        """
        file_count = len(file_paths)

        # Validate strategy hint if provided
        if strategy_hint and strategy_hint not in self._strategies:
            logger.warning(f"Invalid strategy hint '{strategy_hint}', ignoring")
            strategy_hint = None

        # Use explicit hint if provided and valid
        if strategy_hint and strategy_hint in self._strategies:
            logger.debug(f"Using explicit strategy hint: {strategy_hint}")
            return self._strategies[strategy_hint]

        # Auto-select based on file count
        if file_count >= self.streaming_threshold:
            logger.debug(f"Auto-selected streaming strategy for {file_count} files")
            return self._strategies["streaming"]
        elif file_count >= self.chunk_threshold:
            logger.debug(f"Auto-selected chunked strategy for {file_count} files")
            return self._strategies["chunked"]
        else:
            logger.debug(f"Auto-selected standard strategy for {file_count} files")
            return self._strategies["standard"]

    def get_available_strategies(self) -> list[str]:
        """Get list of available strategy names."""
        return list(self._strategies.keys())

    def add_custom_strategy(self, name: str, strategy: DataLoadingStrategy) -> None:
        """Add a custom loading strategy."""
        self._strategies[name] = strategy

    def remove_strategy(self, name: str) -> None:
        """Remove a loading strategy."""
        if name in ["standard", "chunked", "streaming"]:
            raise ValueError(f"Cannot remove built-in strategy: {name}")
        self._strategies.pop(name, None)


# Factory function for easy instantiation
def create_loading_strategy_selector(
    chunk_threshold: int = 30, streaming_threshold: int = 100, default_chunk_size: int = 10
) -> LoadingStrategySelector:
    """Factory function to create a loading strategy selector with default configuration."""
    return LoadingStrategySelector(chunk_threshold, streaming_threshold, default_chunk_size)
