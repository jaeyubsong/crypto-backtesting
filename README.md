# Crypto Trading Backtesting Platform

A comprehensive cryptocurrency backtesting platform that enables quantitative traders to develop, test, and analyze algorithmic trading strategies using historical market data.

## 📊 Project Status

**Current Phase:** Active Development - Phase 3 (Data Layer Implementation)

### ✅ Completed Features
- **Core Domain Models**: Position, Trade, and Portfolio models with full functionality
- **Type Safety**: Strict typing with Symbol, TradingMode, PositionType, and ActionType enums
- **Portfolio Management**: Complete buy/sell/close operations with leverage support (1x-100x)
- **Risk Management**: Margin calculations, liquidation detection, and position limits
- **Trading Modes**: Separate logic for SPOT and FUTURES trading
- **Exception Handling**: Comprehensive domain-specific exception hierarchy
- **Data Pipeline**: Automated Binance data download and OHLCV conversion
- **Testing Infrastructure**: 130+ unit tests with 90-100% coverage on core modules

### 🚧 In Progress
- Data layer implementation for efficient historical data loading
- Strategy framework with security sandbox

### 📋 Upcoming
- Backtesting engine core
- FastAPI backend implementation
- Web-based frontend interface
- Performance metrics calculator

## 🚀 Features

- **High-Performance Backtesting Engine**: Test strategies on historical crypto data with realistic trading conditions
- **Multi-Timeframe Support**: Backtest on 1m, 5m, 15m, 1h, 4h, and 1d timeframes
- **Futures & Spot Trading**: Support for both spot and futures trading with leverage
- **Advanced Portfolio Management**: Realistic position sizing, margin management, and liquidation handling
- **Comprehensive Metrics**: Sharpe ratio, Sortino ratio, max drawdown, win rate, and more
- **Strategy Framework**: Easy-to-use Python framework for strategy development
- **Data Conversion Tools**: Convert raw Binance trade data to OHLCV format
- **RESTful API**: FastAPI-based backend with comprehensive endpoints
- **Web Interface**: Interactive frontend for strategy configuration and results visualization

## 📋 Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) for dependency management

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd crypto-trading
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up pre-commit hooks** (optional but recommended):
   ```bash
   uv run pre-commit install
   ```

## 📊 Data Preparation

The platform requires OHLCV (Open, High, Low, Close, Volume) data in CSV format.

### Downloading Binance Data

The platform includes an automated data downloader for Binance futures data:

```bash
# Download and convert data for date range
uv run python scripts/download_binance_data.py --symbol BTCUSDT --start-date 2025-01-01 --end-date 2025-01-03 --convert --timeframes 1m 5m 1h

# Download single day without conversion
uv run python scripts/download_binance_data.py --symbol BTCUSDT --start-date 2025-01-01 --end-date 2025-01-01

# See all options
uv run python scripts/download_binance_data.py --help
```

### Converting Existing Trade Data

If you have raw Binance trade data, use the conversion script:

```bash
# Convert all files in data/raw/binance/
uv run python scripts/convert_trades_to_ohlcv.py --timeframes 1m 5m 1h

# Convert a specific file
uv run python scripts/convert_trades_to_ohlcv.py --file BTCUSDT-trades-2025-09-08.csv --timeframes 1m

# See all options
uv run python scripts/convert_trades_to_ohlcv.py --help
```

### Data Structure

The platform organizes data in a daily file structure for better performance:

```
data/
├── binance/
│   ├── spot/
│   │   └── BTCUSDT/
│   │       ├── 1m/
│   │       │   ├── BTCUSDT_1m_2025-01-01.csv
│   │       │   ├── BTCUSDT_1m_2025-01-02.csv
│   │       │   └── ...
│   │       ├── 5m/
│   │       │   ├── BTCUSDT_5m_2025-01-01.csv
│   │       │   └── ...
│   │       └── 1h/
│   │           └── ...
│   └── futures/
│       └── BTCUSDT/
│           ├── 1m/
│           ├── 5m/
│           └── 1h/
```

Each CSV file contains OHLCV data for a single day:
```csv
timestamp,open,high,low,close,volume
1609459200000,29000.00,29500.00,28800.00,29200.00,1234.567
1609459260000,29200.00,29300.00,29100.00,29150.00,987.654
```

## 🚀 Quick Start

### 1. Start the Development Server

```bash
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Open the Web Interface

Navigate to `http://localhost:8000` in your browser.

### 3. Create Your First Strategy

```python
class SimpleMAStrategy(Strategy):
    def initialize(self):
        self.ma_period = 20
        self.position_size = 1000  # USD

    def on_data(self, data):
        # Calculate simple moving average
        if len(self.portfolio.portfolio_history) >= self.ma_period:
            recent_prices = [h['close'] for h in self.portfolio.portfolio_history[-self.ma_period:]]
            ma = sum(recent_prices) / len(recent_prices)

            current_price = data['close']

            # Buy signal: price crosses above MA
            if current_price > ma and self.get_position_size() == 0:
                self.buy(self.position_size, leverage=2.0)

            # Sell signal: price crosses below MA
            elif current_price < ma and self.get_position_size() > 0:
                self.close_position()
```

## 🧪 Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_engine.py -v

# Run with coverage
uv run pytest --cov
```

### Code Quality

```bash
# Lint code
uv run ruff check

# Fix linting issues
uv run ruff check --fix

# Format code
uv run ruff format

# Type checking with mypy
uv run mypy src tests

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

### Test-Driven Development

This project follows strict TDD principles:

1. **RED**: Write a failing test first
2. **GREEN**: Write minimal code to make the test pass
3. **REFACTOR**: Improve the code while keeping tests green

```bash
# TDD workflow example
uv run pytest tests/test_portfolio.py::test_buy_order -v  # Should fail
# Implement minimal code
uv run pytest tests/test_portfolio.py::test_buy_order -v  # Should pass
# Refactor and ensure tests still pass
```

## 📡 API Documentation

Once the server is running, visit:

- **Interactive API Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

### Key Endpoints

- `POST /api/backtest` - Submit a new backtest
- `GET /api/backtest/{backtest_id}` - Get backtest results
- `GET /api/data/symbols` - List available symbols
- `GET /api/data/history` - Get historical data

## 🏗️ Architecture

### Project Structure

```
src/
├── core/               # Domain logic (no external dependencies)
│   ├── models/        # Domain models (Position, Trade, Portfolio)
│   ├── interfaces/    # Abstract interfaces (IStrategy, IPortfolio, etc.)
│   ├── enums/        # Type-safe enumerations
│   ├── exceptions/   # Domain-specific exceptions
│   ├── constants.py  # System constants and limits
│   ├── types.py      # Protocol types to avoid circular imports
│   └── utils/        # Validation utilities
├── infrastructure/    # External dependencies
│   ├── data/         # Data access layer
│   └── storage/      # File/DB storage
├── application/      # Use cases and services
│   ├── services/     # Business logic services
│   └── dto/         # Data transfer objects
├── api/             # FastAPI application and routers
│   ├── routers/     # API endpoints
│   └── schemas/     # Pydantic schemas
└── backtesting/     # Legacy compatibility layer

data/                  # Market data (gitignored)
results/               # Backtest results (gitignored)
scripts/               # Data processing scripts
tests/                 # Test files
static/                # Frontend assets
```

### Key Components

#### Implemented ✅
- **Portfolio**: Complete position and risk management with margin/leverage support
- **Position**: Trade position tracking with PnL calculations
- **Trade**: Individual trade records with fees and realized PnL
- **Enums**: Type-safe Symbol, TradingMode, PositionType, ActionType
- **Exceptions**: Domain-specific error handling (ValidationError, InsufficientFundsError, etc.)
- **Validation**: Input validation utilities for consistency

#### In Development 🚧
- **DataLoader**: Historical data management (Phase 3)
- **Strategy**: Base class for trading strategies (Phase 5)
- **BacktestEngine**: Core backtesting logic (Phase 6)
- **MetricsCalculator**: Performance analysis (Phase 7)

## 📈 Performance Metrics

The platform calculates comprehensive performance metrics:

- **Return Metrics**: Total return, annualized return, CAGR
- **Risk Metrics**: Sharpe ratio, Sortino ratio, maximum drawdown
- **Trading Metrics**: Win rate, profit factor, average win/loss
- **Futures-Specific**: Average leverage, liquidation count, margin ratio

## 🔒 Security

- **Strategy Sandboxing**: User strategies run in a restricted environment
- **Input Validation**: All inputs are validated using Pydantic schemas
- **Import Restrictions**: Limited library imports in strategy code
- **Resource Limits**: Execution timeouts and memory limits

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Follow TDD principles: write tests first
4. Ensure all tests pass: `uv run pytest`
5. Submit a pull request

### Code Standards

- **SOLID Principles**: Strictly enforced across all modules
- **Type Safety**: Full type hints with mypy strict mode
- **File Guidelines**: Target 150-200 lines per class, maximum 300 lines (business justification required for exceptions)
- **Function Limits**: Maximum 30 lines per function
- **Documentation**: Docstrings required on all public APIs
- **Test Coverage**: Minimum 80% overall, 90%+ for core logic
- **TDD Mandatory**: Tests written FIRST for all business logic
- **Import Rules**: Core layer has NO external dependencies
- **Validation**: All inputs validated at boundaries
- **Design Focus**: Single Responsibility Principle drives class splitting decisions

## 📝 License

[MIT License](LICENSE)

## 🙋‍♂️ Support

For questions or issues, please open a GitHub issue or contact the development team.

## 📚 Documentation

- **[Product Requirements Document (PRD)](PRD.md)**: Business requirements and feature specifications
- **[Technical Specification](TECHNICAL_SPEC.md)**: Detailed technical architecture and design
- **[Implementation Plan](IMPLEMENTATION_PLAN.md)**: Development phases and progress tracking
- **[Claude AI Instructions](CLAUDE.md)**: Development standards and AI assistance guidelines

---

**Built with ❤️ for quantitative cryptocurrency traders**
