"""
Unit tests for Backtest configuration and results models.
Following TDD approach - write failing tests first.
"""

from datetime import UTC, datetime

from src.core.enums import ActionType, PositionType, Symbol, Timeframe, TradingMode
from src.core.models.backtest import BacktestConfig, BacktestResults
from src.core.models.position import Trade


class TestBacktestConfig:
    """Test suite for BacktestConfig model."""

    def test_should_create_backtest_config_with_all_parameters(self) -> None:
        """Test creation of backtest configuration."""
        start_date = datetime(2025, 1, 1, tzinfo=UTC)
        end_date = datetime(2025, 1, 31, tzinfo=UTC)

        config = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10000.0,
            trading_mode=TradingMode.FUTURES,
            max_leverage=10.0,
            maintenance_margin_rate=0.005,
        )

        assert config.symbol == Symbol.BTC
        assert config.timeframe == Timeframe.H1
        assert config.start_date == start_date
        assert config.end_date == end_date
        assert config.initial_capital == 10000.0
        assert config.trading_mode == TradingMode.FUTURES
        assert config.max_leverage == 10.0
        assert config.maintenance_margin_rate == 0.005

    def test_should_validate_date_range(self) -> None:
        """Test that backtest config validates date range."""
        start_date = datetime(2025, 1, 1, tzinfo=UTC)
        end_date = datetime(2025, 1, 31, tzinfo=UTC)

        config = BacktestConfig(
            symbol=Symbol.ETH,
            timeframe=Timeframe.M5,
            start_date=start_date,
            end_date=end_date,
            initial_capital=5000.0,
            trading_mode=TradingMode.SPOT,
            max_leverage=1.0,
            maintenance_margin_rate=0.0,
        )

        assert config.is_valid_date_range()
        assert config.duration_days() == 30

    def test_should_detect_invalid_date_range(self) -> None:
        """Test detection of invalid date ranges."""
        start_date = datetime(2025, 1, 31, tzinfo=UTC)
        end_date = datetime(2025, 1, 1, tzinfo=UTC)  # End before start

        config = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10000.0,
            trading_mode=TradingMode.FUTURES,
            max_leverage=5.0,
            maintenance_margin_rate=0.005,
        )

        assert not config.is_valid_date_range()

    def test_should_validate_trading_parameters(self) -> None:
        """Test validation of trading parameters."""
        config = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=datetime(2025, 1, 1, tzinfo=UTC),
            end_date=datetime(2025, 1, 31, tzinfo=UTC),
            initial_capital=10000.0,
            trading_mode=TradingMode.FUTURES,
            max_leverage=50.0,
            maintenance_margin_rate=0.01,
        )

        assert config.is_valid_leverage()
        assert config.is_valid_capital()
        assert config.is_valid_margin_rate()

    def test_should_detect_invalid_trading_parameters(self) -> None:
        """Test detection of invalid trading parameters."""
        # Invalid leverage (too high)
        config_high_leverage = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=datetime(2025, 1, 1, tzinfo=UTC),
            end_date=datetime(2025, 1, 31, tzinfo=UTC),
            initial_capital=10000.0,
            trading_mode=TradingMode.FUTURES,
            max_leverage=150.0,  # Too high
            maintenance_margin_rate=0.005,
        )

        assert not config_high_leverage.is_valid_leverage()

        # Invalid capital (negative)
        config_negative_capital = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=datetime(2025, 1, 1, tzinfo=UTC),
            end_date=datetime(2025, 1, 31, tzinfo=UTC),
            initial_capital=-1000.0,  # Negative
            trading_mode=TradingMode.FUTURES,
            max_leverage=10.0,
            maintenance_margin_rate=0.005,
        )

        assert not config_negative_capital.is_valid_capital()

    def test_should_convert_to_dict(self) -> None:
        """Test conversion of config to dictionary."""
        start_date = datetime(2025, 1, 1, tzinfo=UTC)
        end_date = datetime(2025, 1, 31, tzinfo=UTC)

        config = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10000.0,
            trading_mode=TradingMode.FUTURES,
            max_leverage=10.0,
            maintenance_margin_rate=0.005,
        )

        config_dict = config.to_dict()

        assert config_dict["symbol"] == Symbol.BTC.value
        assert config_dict["timeframe"] == Timeframe.H1.value
        assert config_dict["initial_capital"] == 10000.0
        assert config_dict["trading_mode"] == TradingMode.FUTURES.value


class TestBacktestResults:
    """Test suite for BacktestResults model."""

    def test_should_create_successful_backtest_results(self) -> None:
        """Test creation of successful backtest results."""
        start_date = datetime(2025, 1, 1, tzinfo=UTC)
        end_date = datetime(2025, 1, 31, tzinfo=UTC)

        config = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10000.0,
            trading_mode=TradingMode.FUTURES,
            max_leverage=10.0,
            maintenance_margin_rate=0.005,
        )

        trade = Trade(
            timestamp=datetime.now(UTC),
            symbol=Symbol.BTC,
            action=ActionType.SELL,
            quantity=1.0,
            price=52000.0,
            leverage=2.0,
            fee=26.0,
            position_type=PositionType.LONG,
            pnl=1974.0,
            margin_used=0.0,
        )

        portfolio_history = [
            {"timestamp": start_date, "portfolio_value": 10000.0},
            {"timestamp": end_date, "portfolio_value": 11974.0},
        ]

        metrics = {
            "total_return": 19.74,
            "sharpe_ratio": 1.5,
            "max_drawdown": -5.2,
            "total_trades": 2,
            "win_rate": 100.0,
        }

        results = BacktestResults(
            config=config,
            trades=[trade],
            portfolio_history=portfolio_history,
            metrics=metrics,
            status="completed",
        )

        assert results.config == config
        assert len(results.trades) == 1
        assert results.trades[0] == trade
        assert len(results.portfolio_history) == 2
        assert results.metrics == metrics
        assert results.status == "completed"
        assert results.error_message is None

    def test_should_create_failed_backtest_results(self) -> None:
        """Test creation of failed backtest results."""
        config = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=datetime(2025, 1, 1, tzinfo=UTC),
            end_date=datetime(2025, 1, 31, tzinfo=UTC),
            initial_capital=10000.0,
            trading_mode=TradingMode.FUTURES,
            max_leverage=10.0,
            maintenance_margin_rate=0.005,
        )

        results = BacktestResults(
            config=config,
            trades=[],
            portfolio_history=[],
            metrics={},
            status="failed",
            error_message="Strategy compilation error",
        )

        assert results.status == "failed"
        assert results.error_message == "Strategy compilation error"
        assert len(results.trades) == 0
        assert len(results.portfolio_history) == 0
        assert len(results.metrics) == 0

    def test_should_calculate_performance_summary(self) -> None:
        """Test performance summary calculation."""
        config = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=datetime(2025, 1, 1, tzinfo=UTC),
            end_date=datetime(2025, 1, 31, tzinfo=UTC),
            initial_capital=10000.0,
            trading_mode=TradingMode.FUTURES,
            max_leverage=10.0,
            maintenance_margin_rate=0.005,
        )

        portfolio_history = [
            {"timestamp": datetime(2025, 1, 1, tzinfo=UTC), "portfolio_value": 10000.0},
            {"timestamp": datetime(2025, 1, 15, tzinfo=UTC), "portfolio_value": 9500.0},
            {"timestamp": datetime(2025, 1, 31, tzinfo=UTC), "portfolio_value": 12000.0},
        ]

        metrics = {
            "total_return": 20.0,
            "sharpe_ratio": 1.8,
            "max_drawdown": -5.0,
            "total_trades": 5,
            "win_rate": 80.0,
        }

        results = BacktestResults(
            config=config,
            trades=[],
            portfolio_history=portfolio_history,
            metrics=metrics,
            status="completed",
        )

        summary = results.performance_summary()

        assert summary["initial_value"] == 10000.0
        assert summary["final_value"] == 12000.0
        assert summary["total_return"] == 20.0
        assert summary["duration_days"] == 30

    def test_should_check_if_profitable(self) -> None:
        """Test profitability check."""
        config = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=datetime(2025, 1, 1, tzinfo=UTC),
            end_date=datetime(2025, 1, 31, tzinfo=UTC),
            initial_capital=10000.0,
            trading_mode=TradingMode.FUTURES,
            max_leverage=10.0,
            maintenance_margin_rate=0.005,
        )

        # Profitable results
        profitable_results = BacktestResults(
            config=config,
            trades=[],
            portfolio_history=[
                {"timestamp": datetime(2025, 1, 1, tzinfo=UTC), "portfolio_value": 10000.0},
                {"timestamp": datetime(2025, 1, 31, tzinfo=UTC), "portfolio_value": 12000.0},
            ],
            metrics={"total_return": 20.0},
            status="completed",
        )

        assert profitable_results.is_profitable()

        # Loss-making results
        loss_results = BacktestResults(
            config=config,
            trades=[],
            portfolio_history=[
                {"timestamp": datetime(2025, 1, 1, tzinfo=UTC), "portfolio_value": 10000.0},
                {"timestamp": datetime(2025, 1, 31, tzinfo=UTC), "portfolio_value": 8000.0},
            ],
            metrics={"total_return": -20.0},
            status="completed",
        )

        assert not loss_results.is_profitable()

    def test_should_convert_to_dict(self) -> None:
        """Test conversion of results to dictionary."""
        config = BacktestConfig(
            symbol=Symbol.BTC,
            timeframe=Timeframe.H1,
            start_date=datetime(2025, 1, 1, tzinfo=UTC),
            end_date=datetime(2025, 1, 31, tzinfo=UTC),
            initial_capital=10000.0,
            trading_mode=TradingMode.FUTURES,
            max_leverage=10.0,
            maintenance_margin_rate=0.005,
        )

        results = BacktestResults(
            config=config,
            trades=[],
            portfolio_history=[],
            metrics={"total_return": 15.5},
            status="completed",
        )

        results_dict = results.to_dict()

        assert results_dict["status"] == "completed"
        assert results_dict["metrics"]["total_return"] == 15.5
        assert "config" in results_dict
        assert results_dict["error_message"] is None
