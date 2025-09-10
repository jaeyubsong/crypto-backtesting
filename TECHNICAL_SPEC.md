# Technical Specification: Crypto Quant Backtesting Platform

**Version:** 1.0
**Date:** September 10, 2025

## 1. System Architecture Overview

### 1.1. High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   Backtesting   │
│   (HTML/JS)     │◄──►│   Backend       │◄──►│   Engine        │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Results       │    │   Market Data   │
                       │   Storage       │    │   (CSV Files)   │
                       │   (JSON/CSV)    │    │                 │
                       └─────────────────┘    └─────────────────┘
```

### 1.2. Project Structure

```
crypto-trading/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── backtest.py      # Backtest endpoints
│   │   │   └── data.py          # Data endpoints
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── request.py       # API request models
│   │       └── response.py      # API response models
│   ├── backtesting/
│   │   ├── __init__.py
│   │   ├── engine.py            # Core backtesting engine
│   │   ├── portfolio.py         # Portfolio management
│   │   ├── strategy.py          # Strategy base class
│   │   ├── executor.py          # Strategy execution
│   │   └── metrics.py           # Performance calculations
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py            # Data loading utilities
│   │   └── processor.py         # Data processing utilities
│   └── utils/
│       ├── __init__.py
│       ├── validators.py        # Input validation
│       └── exceptions.py        # Custom exceptions
├── data/
│   └── binance/
│       ├── spot/
│       │   ├── BTCUSDT_1m.csv
│       │   └── ...
│       └── futures/
│           ├── BTCUSDT_1m.csv
│           └── ...
├── results/
│   └── backtests/
│       ├── {backtest_id}/
│       │   ├── config.json
│       │   ├── trades.csv
│       │   ├── portfolio.csv
│       │   └── metrics.json
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── tests/
├── pyproject.toml
├── CLAUDE.md
├── PRD.md
└── TECHNICAL_SPEC.md
```

## 2. Data Models and Storage

### 2.1. Market Data Format (CSV)

**Daily File Structure**: Data is organized in daily files for better performance and memory management.

**Directory Structure**:
```
data/binance/{spot|futures}/{SYMBOL}/{TIMEFRAME}/
```

**File naming convention**: `{SYMBOL}_{TIMEFRAME}_{YYYY-MM-DD}.csv`

**Example Structure**:
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
│   │       └── 1h/
│   └── futures/
│       └── BTCUSDT/
│           ├── 1m/
│           ├── 5m/
│           └── 1h/
```

**CSV Structure**:
```csv
timestamp,open,high,low,close,volume
1609459200000,29000.00,29500.00,28800.00,29200.00,1234.567
1609459260000,29200.00,29300.00,29100.00,29150.00,987.654
```

**Fields**:
- `timestamp`: Unix timestamp in milliseconds
- `open`: Opening price (float)
- `high`: Highest price (float)
- `low`: Lowest price (float)
- `close`: Closing price (float)
- `volume`: Trading volume (float)

**Benefits of Daily Files**:
- Faster loading for specific date ranges
- Better memory management for large datasets
- Easier parallel processing
- Simplified data management and archiving

### 2.2. Backtest Results Storage

**Directory structure**: `results/backtests/{backtest_id}/`

**config.json** - Backtest configuration:
```json
{
  "backtest_id": "bt_20250910_123456",
  "strategy_code": "class MyStrategy(Strategy): ...",
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 10000,
  "trading_mode": "futures",
  "max_leverage": 10,
  "created_at": "2025-09-10T12:34:56Z",
  "status": "completed",
  "error_message": null
}
```

**trades.csv** - Individual trades:
```csv
timestamp,action,symbol,quantity,price,leverage,fee,position_type,pnl
1609459200000,buy,BTCUSDT,0.5,29000.00,2.0,2.9,long,0
1609462800000,sell,BTCUSDT,0.5,29500.00,2.0,2.95,long,247.1
```

**portfolio.csv** - Portfolio snapshots:
```csv
timestamp,portfolio_value,cash,unrealized_pnl,realized_pnl,margin_used,leverage_ratio
1609459200000,10000.00,5000.00,0,0,5000.00,2.0
1609459260000,10025.00,5000.00,25.00,0,5000.00,2.0
```

**metrics.json** - Performance metrics:
```json
{
  "total_return": 15.5,
  "sharpe_ratio": 1.2,
  "max_drawdown": -8.3,
  "total_trades": 45,
  "win_rate": 60.5,
  "profit_factor": 1.8,
  "liquidations": 2,
  "average_leverage": 3.2
}
```

## 3. API Design

### 3.1. FastAPI Application Structure

**main.py**:
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routers import backtest, data

app = FastAPI(title="Crypto Backtesting API", version="1.0.0")

app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(data.router, prefix="/api/data", tags=["data"])

app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

### 3.2. API Endpoints

#### 3.2.1. POST /api/backtest

**Request Model**:
```python
class BacktestRequest(BaseModel):
    strategy_code: str
    symbol: str
    timeframe: str  # "1m", "5m", "1h", "4h", "1d"
    start_date: str  # "2024-01-01"
    end_date: str    # "2024-12-31"
    initial_capital: float = 10000.0
    trading_mode: str = "spot"  # "spot" or "futures"
    max_leverage: float = 1.0
    maintenance_margin_rate: float = 0.005  # 0.5%
```

**Response Model**:
```python
class BacktestResponse(BaseModel):
    backtest_id: str
    status: str  # "running", "completed", "failed"
    message: str
```

#### 3.2.2. GET /api/backtest/{backtest_id}

**Response Model**:
```python
class BacktestResults(BaseModel):
    backtest_id: str
    status: str
    config: dict
    metrics: Optional[dict]
    trades: Optional[List[dict]]
    portfolio_history: Optional[List[dict]]
    error_message: Optional[str]
```

#### 3.2.3. GET /api/data/symbols

**Response Model**:
```python
class SymbolsResponse(BaseModel):
    symbols: List[str]
    trading_modes: List[str]  # ["spot", "futures"]
```

#### 3.2.4. GET /api/data/history

**Query Parameters**:
- `symbol`: str
- `timeframe`: str
- `start_date`: Optional[str]
- `end_date`: Optional[str]
- `limit`: Optional[int] = 1000

**Response Model**:
```python
class HistoricalData(BaseModel):
    symbol: str
    timeframe: str
    data: List[dict]  # OHLCV data
```

## 4. Backtesting Engine Implementation

### 4.1. Core Engine Architecture

**engine.py**:
```python
class BacktestEngine:
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.portfolio = Portfolio(config.initial_capital, config.trading_mode)
        self.data_loader = DataLoader()
        self.metrics_calculator = MetricsCalculator()

    async def run_backtest(self, strategy_code: str) -> BacktestResults:
        # 1. Load and validate market data
        # 2. Execute user strategy
        # 3. Calculate metrics
        # 4. Save results
        pass
```

### 4.2. Portfolio Management

**portfolio.py**:
```python
class Portfolio:
    def __init__(self, initial_capital: float, trading_mode: str):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {symbol: Position}
        self.trading_mode = trading_mode
        self.trades = []
        self.portfolio_history = []

    def buy(self, symbol: str, quantity: float, price: float, leverage: float = 1.0):
        # Implementation for long positions
        pass

    def sell(self, symbol: str, quantity: float, price: float, leverage: float = 1.0):
        # Implementation for short positions
        pass

    def close_position(self, symbol: str, percentage: float = 100.0):
        # Close partial or full position
        pass

    def check_liquidation(self, current_prices: dict) -> List[str]:
        # Check for liquidation conditions
        pass

    def calculate_margin_ratio(self) -> float:
        # Calculate current margin ratio
        pass
```

### 4.3. Strategy Framework

**strategy.py**:
```python
from abc import ABC, abstractmethod
import pandas as pd

class Strategy(ABC):
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio
        self.indicators = {}

    @abstractmethod
    def initialize(self):
        """Called once at the start of backtesting"""
        pass

    @abstractmethod
    def on_data(self, data: pd.Series):
        """Called for each new data point"""
        pass

    # Trading API
    def buy(self, amount: float, leverage: float = 1.0):
        return self.portfolio.buy(self.symbol, amount, self.current_price, leverage)

    def sell(self, amount: float, leverage: float = 1.0):
        return self.portfolio.sell(self.symbol, amount, self.current_price, leverage)

    def close_position(self, percentage: float = 100.0):
        return self.portfolio.close_position(self.symbol, percentage)

    # Information API
    def get_position_size(self) -> float:
        return self.portfolio.get_position_size(self.symbol)

    def get_cash(self) -> float:
        return self.portfolio.cash

    def get_margin_ratio(self) -> float:
        return self.portfolio.calculate_margin_ratio()

    def get_unrealized_pnl(self) -> float:
        return self.portfolio.get_unrealized_pnl(self.symbol, self.current_price)

    def get_leverage(self) -> float:
        position = self.portfolio.positions.get(self.symbol)
        return position.leverage if position else 0.0
```

### 4.4. Strategy Execution

**executor.py**:
```python
class StrategyExecutor:
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    def execute_strategy(self, strategy_code: str, market_data: pd.DataFrame) -> ExecutionResults:
        try:
            # 1. Create strategy class from user code
            strategy_class = self._compile_strategy(strategy_code)
            strategy = strategy_class(self.portfolio)

            # 2. Initialize strategy
            strategy.initialize()

            # 3. Run strategy on historical data
            for timestamp, row in market_data.iterrows():
                strategy.symbol = row['symbol']  # Set current symbol
                strategy.current_price = row['close']  # Set current price
                strategy.timestamp = timestamp

                # Check for liquidations first
                liquidated = self.portfolio.check_liquidation({row['symbol']: row['close']})

                # Execute strategy logic
                strategy.on_data(row)

            return ExecutionResults(success=True, error=None)

        except Exception as e:
            return ExecutionResults(success=False, error=str(e))

    def _compile_strategy(self, strategy_code: str) -> type:
        # Safely compile and execute user strategy code
        # Apply import restrictions
        # Return strategy class
        pass
```

## 5. Security and Validation

### 5.1. Strategy Code Restrictions

**validators.py**:
```python
ALLOWED_IMPORTS = {
    'pandas', 'numpy', 'pandas_ta', 'talib', 'math', 'datetime'
}

FORBIDDEN_KEYWORDS = {
    'import os', 'import sys', 'exec', 'eval', 'open', '__import__',
    'subprocess', 'requests', 'urllib', 'socket'
}

def validate_strategy_code(code: str) -> ValidationResult:
    # Check for forbidden imports and keywords
    # Validate strategy class structure
    # Return validation result
    pass
```

### 5.2. Input Validation

```python
class BacktestConfig:
    def __init__(self, **kwargs):
        self.symbol = self._validate_symbol(kwargs['symbol'])
        self.timeframe = self._validate_timeframe(kwargs['timeframe'])
        self.start_date = self._validate_date(kwargs['start_date'])
        self.end_date = self._validate_date(kwargs['end_date'])
        self.initial_capital = self._validate_positive_float(kwargs['initial_capital'])
        self.max_leverage = self._validate_leverage(kwargs.get('max_leverage', 1.0))
```

## 6. Performance Metrics

### 6.1. Metrics Calculation

**metrics.py**:
```python
class MetricsCalculator:
    def calculate_all_metrics(self, portfolio_history: pd.DataFrame, trades: pd.DataFrame) -> dict:
        return {
            'total_return': self._calculate_total_return(portfolio_history),
            'sharpe_ratio': self._calculate_sharpe_ratio(portfolio_history),
            'sortino_ratio': self._calculate_sortino_ratio(portfolio_history),
            'max_drawdown': self._calculate_max_drawdown(portfolio_history),
            'volatility': self._calculate_volatility(portfolio_history),
            'total_trades': len(trades),
            'win_rate': self._calculate_win_rate(trades),
            'profit_factor': self._calculate_profit_factor(trades),
            'avg_win': self._calculate_avg_win(trades),
            'avg_loss': self._calculate_avg_loss(trades),
            'liquidations': self._count_liquidations(trades),
            'avg_leverage': self._calculate_avg_leverage(trades),
            'max_leverage': self._calculate_max_leverage(trades),
        }
```

## 7. Frontend Implementation

### 7.1. Basic HTML Structure

**index.html**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Crypto Backtesting Platform</title>
    <link rel="stylesheet" href="style.css">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <div id="app">
        <!-- Strategy Input -->
        <section id="strategy-section">
            <h2>Strategy Configuration</h2>
            <textarea id="strategy-code" placeholder="Enter your strategy code here..."></textarea>
            <!-- Configuration inputs -->
        </section>

        <!-- Results Display -->
        <section id="results-section">
            <div id="chart-container"></div>
            <div id="metrics-container"></div>
        </section>
    </div>
    <script src="app.js"></script>
</body>
</html>
```

### 7.2. JavaScript Implementation

**app.js**:
```javascript
class BacktestingApp {
    constructor() {
        this.baseUrl = '/api';
        this.currentBacktestId = null;
    }

    async submitBacktest() {
        const config = this.getBacktestConfig();
        try {
            const response = await fetch(`${this.baseUrl}/backtest`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            const result = await response.json();
            this.currentBacktestId = result.backtest_id;
            this.pollBacktestStatus();
        } catch (error) {
            this.displayError(error);
        }
    }

    async pollBacktestStatus() {
        // Poll backtest status and display results when complete
    }

    displayResults(results) {
        this.displayChart(results.portfolio_history, results.trades);
        this.displayMetrics(results.metrics);
    }
}
```

## 8. Error Handling and Logging

### 8.1. Exception Hierarchy

**exceptions.py**:
```python
class BacktestError(Exception):
    """Base exception for backtesting errors"""
    pass

class StrategyError(BacktestError):
    """Strategy compilation/execution errors"""
    pass

class DataError(BacktestError):
    """Data loading/processing errors"""
    pass

class ValidationError(BacktestError):
    """Input validation errors"""
    pass
```

### 8.2. Error Response Format

```python
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None
    backtest_id: Optional[str] = None
```

## 9. Testing Strategy

### 9.1. Unit Tests Structure

```
tests/
├── test_engine.py          # Core engine tests
├── test_portfolio.py       # Portfolio management tests
├── test_strategy.py        # Strategy framework tests
├── test_metrics.py         # Performance metrics tests
├── test_api.py            # API endpoint tests
└── fixtures/
    ├── sample_data.csv     # Test market data
    └── sample_strategies.py # Test strategy code
```

### 9.2. Sample Test Strategy

```python
# Sample strategy for testing
class SimpleMAStrategy(Strategy):
    def initialize(self):
        self.ma_period = 20

    def on_data(self, data):
        # Simple moving average crossover strategy
        if len(self.portfolio.portfolio_history) >= self.ma_period:
            recent_prices = [h['price'] for h in self.portfolio.portfolio_history[-self.ma_period:]]
            ma = sum(recent_prices) / len(recent_prices)

            if data['close'] > ma and self.get_position_size() == 0:
                self.buy(1000, leverage=2.0)  # Buy with 2x leverage
            elif data['close'] < ma and self.get_position_size() > 0:
                self.close_position()
```

## 10. Deployment and Configuration

### 10.1. Development Setup

**Commands to add to CLAUDE.md**:
```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Download and convert Binance data
uv run python scripts/download_binance_data.py --symbol BTCUSDT --start-date 2025-01-01 --end-date 2025-01-03 --convert --timeframes 1m 5m 1h

# Convert existing raw data
uv run python scripts/convert_trades_to_ohlcv.py --timeframes 1m 5m 1h

# Run tests
uv run pytest tests/

# Format and lint
uv run ruff check --fix
```

### 10.2. Environment Configuration

**config.py**:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    data_directory: str = "data"
    results_directory: str = "results"
    max_backtest_duration: int = 3600  # 1 hour timeout
    allowed_timeframes: List[str] = ["1m", "5m", "15m", "1h", "4h", "1d"]
    max_leverage: float = 100.0
    default_maintenance_margin_rate: float = 0.005

    class Config:
        env_file = ".env"
```

## 11. Future Extension Points

### 11.1. Database Migration Path

When transitioning from CSV to database:
- Replace `DataLoader` with database queries
- Implement result caching layer
- Add backtest history management

### 11.2. Real-time Updates

For React frontend with real-time updates:
- Add WebSocket support to FastAPI
- Implement progress streaming during backtest execution
- Add real-time chart updates

### 11.3. Multi-Asset Support

Extension points for multi-asset backtesting:
- Modify Portfolio to handle multiple positions
- Update strategy framework for multi-symbol data
- Enhance correlation and risk metrics

---

This technical specification provides a comprehensive implementation roadmap for the crypto quant backtesting platform. Each section includes specific implementation details, code structures, and extension points for future enhancements.
