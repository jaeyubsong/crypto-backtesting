# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Crypto-trading backtesting platform for quantitative cryptocurrency traders. Python 3.13+, FastAPI, strict TDD and SOLID principles.

## 🚨 CRITICAL DEVELOPMENT RULES

### ⛔ PROTECTED FILES - NEVER MODIFY
- `.github/workflows/claude.yml`
- `.github/workflows/claude-code-review.yml`

These files are managed externally. Pre-commit hooks will block modifications.

### 1. Test-Driven Development (TDD) - MANDATORY

**ALWAYS follow TDD cycle:**
1. **RED**: Write failing test FIRST
2. **GREEN**: Write minimal code to pass
3. **REFACTOR**: Improve while keeping tests green

**Testing Philosophy:**
- Test BEHAVIOR, not implementation
- Focus on public APIs and critical business logic
- Don't test trivial getters/setters
- Integration tests can cover multiple units

### 2. Quality Gates - MANDATORY Before Every Commit

```bash
# ALL must pass before committing
uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80 &&
uv run ruff check --output-format=github &&
uv run ruff format --check &&
uv run mypy src/ tests/
```

**🚫 NEVER push if any fail:**
- Tests failing
- MyPy type errors
- Ruff linting errors
- Coverage below 80%

**Quick fixes:**
```bash
uv run ruff check --fix && uv run ruff format
uv run pytest -x --tb=short
```

### 3. SOLID Principles (Essential)

- **S**: One reason to change per class/module
- **O**: Open for extension, closed for modification
- **L**: Derived classes substitutable for base classes
- **I**: Many specific interfaces > one general interface
- **D**: Depend on abstractions, not implementations

### 4. Performance Guidelines

**🚀 ACHIEVED: 120-130x faster calculations (Decimal→Float migration)**
- **Memory**: 4x reduction (24 vs 104 bytes per value)
- **Coverage**: 83% maintained (+99 tests)
- **Hot Path Optimization**: Removed redundant validations
- **Bulk Operations**: O(n) → O(k) improvements

**Best Practices:**
- Avoid redundant conversions: `to_float()` on already-float values
- Use native operations where safe
- Cache calculations vs recalculating
- Strategic validation placement
- Bulk operations over loops

### 5. File Organization & Size Guidelines

```
src/
├── core/           # Pure business logic, no external deps
├── infrastructure/ # Data access, caching, storage
├── application/    # Use cases, services, DTOs
└── api/           # FastAPI routers, schemas
```

**Size Limits:**
- **Target**: 150-200 lines per class
- **Standard Max**: 300 lines (split if exceeded)
- **Hard Limit**: 500 lines (architectural review required)
- **Functions**: ≤30 lines, ≤5 parameters
- **Classes**: ≤20 methods

**Import Rules:**
- Core: NO external dependencies
- Infrastructure: Can import core
- Application: Can import core + infrastructure
- API: Can import all layers
- NEVER circular dependencies

### 6. Testing Standards

**Current Status:** 440 tests, 87% coverage
- **Core Domain Models**: 90-100% coverage
- **Portfolio Trading**: 98% coverage (16 tests)
- **Portfolio Risk**: 100% coverage (16 tests)
- **Data Layer (Phase 3)**: 93-94% coverage (csv_cache_core.py, csv_file_loader.py)

**Test Organization:**
```
tests/
├── unit/        # Isolated, mocked dependencies
├── integration/ # Real dependencies
└── fixtures/    # Shared test data
```

**Coverage Guidelines:**
- Overall: ≥80% (✅ Achieved: 87%)
- Core business logic: ≥90% (✅ Achieved: 90-100%)
- Data layer: ≥85% (✅ Achieved: 93-94%)
- API endpoints: ≥85%

## Architecture Patterns

### Composition Pattern (Portfolio)
```python
class Portfolio(IPortfolio):
    def __init__(self, initial_capital: float, trading_mode: TradingMode, max_leverage: float):
        self.core = PortfolioCore(...)
        self.trading = PortfolioTrading(self.core)
        self.risk = PortfolioRisk(self.core)
        self.metrics = PortfolioMetrics(self.core)
```

### Factory Pattern
```python
@classmethod
def create_long(cls, symbol: Symbol, size: float, entry_price: float, **kwargs) -> "Position":
    # Validation and construction logic
    return cls(symbol=symbol, size=abs(size), ...)
```

### Thread Safety
```python
@dataclass
class PortfolioCore:
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def add_position(self, position: Position) -> None:
        with self._lock:
            # Atomic operations
```

### Modular Data Layer (Phase 3)
```python
class CSVCacheCore(CacheSubject, ICacheManager):
    """Core caching functionality with memory management and observer pattern support."""

    def __init__(self, cache_size: int = DEFAULT_CACHE_SIZE, enable_observers: bool = True):
        self.cache: LRUCache[str, pd.DataFrame] = LRUCache(maxsize=cache_size)
        self._cache_lock = RLock()  # Thread-safe cache access
        self._file_stat_cache: TTLCache[str, float] = TTLCache(maxsize=1000, ttl=300)

class CSVFileLoader:
    """Handles loading and validation of individual CSV files."""

    def __init__(self, cache_core: CSVCacheCore):
        self.cache_core = cache_core

    async def load_single_file(self, file_path: Path) -> pd.DataFrame:
        # Observer pattern with deferred notifications
        # Memory-efficient loading with validation
```

## Precision Guidelines

**Float-Based Calculations (MIGRATION COMPLETED)**
- ✅ **Use**: Backtesting, strategy development, research
- 🚫 **Avoid**: Production trading, regulatory reporting

**Safe Operations:**
```python
from src.core.types.financial import safe_float_comparison, validate_safe_float_range

# Use tolerance-based comparisons
if safe_float_comparison(price1, price2, tolerance=1e-9):
    # Handle equal prices

# Validate extreme values
safe_value = validate_safe_float_range(calculation, "context")
```

## Common Commands

### Development
```bash
# Testing
uv run pytest                                    # Run all tests
uv run pytest --cov=src --cov-fail-under=80    # With coverage
uv run pytest tests/test_file.py::test_func -v  # Specific test

# Code Quality
uv run ruff check --fix     # Fix linting
uv run ruff format          # Format code
uv run mypy src/ tests/     # Type checking

# Package Management
uv add <package>            # Add dependency
uv sync                     # Sync dependencies
```

### Project Specific
```bash
# Server
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Data
uv run python scripts/download_binance_data.py --symbol BTCUSDT --start-date 2025-01-01 --end-date 2025-01-03 --convert --timeframes 1m 5m 1h
```

## Code Standards

### Naming Conventions
- Classes: `PascalCase` (`BacktestEngine`)
- Functions/variables: `snake_case` (`calculate_sharpe_ratio`)
- Constants: `UPPER_SNAKE_CASE` (`DEFAULT_LEVERAGE`)
- Private: prefix `_` (`_validate_input`)

### Documentation Requirements
- Every module: purpose docstring
- Every class: responsibility docstring
- Every public method: parameters and return types
- Type hints everywhere

### Error Handling
```python
BacktestException (base)
├── ValidationError (invalid input)
├── DataError (data access)
├── StrategyError (strategy execution)
├── CalculationError (metrics/math)
└── ConfigurationError (setup)
```

## Commit Standards

**Commit after every:**
- Test written (even failing)
- Test passing
- Refactoring completed
- Feature completed

**Message format:**
```
test: Add test for [feature]
feat: Implement [feature]
fix: Resolve [issue]
refactor: Improve [component]
docs: Update [documentation]
```

## Performance Targets

- API endpoints: <200ms (p95)
- Backtest execution: <1s per 1000 candles
- Data loading: <500ms per file
- Memory: <1GB for typical backtest

## Security

**Input Validation:**
- Validate ALL user inputs
- Use Pydantic for schemas
- Sanitize file paths
- Limit upload sizes

**Code Execution:**
- Sandbox user strategies
- Restrict imports
- Set timeouts
- Monitor resources

## Logging (Loguru)

**Setup:**
```python
from loguru import logger
logger.remove()
logger.add(sys.stderr, format="<green>{time}</green> | <level>{level}</level> | {message}", level="INFO")
```

**Levels:** TRACE < DEBUG < INFO < SUCCESS < WARNING < ERROR < CRITICAL

**What to Log:**
- ✅ API requests, business transactions, errors with context
- ❌ Passwords, PII, secrets, API keys

**Example:**
```python
logger.info("Backtest completed", backtest_id=id, duration=duration, trades=len(trades))
```

## Code Review Checklist

- [x] TDD followed (test first)
- [x] All tests passing (440/446 - 440 passed, 6 skipped)
- [x] Coverage ≥80% (87% achieved)
- [x] No linting/type errors
- [x] SOLID principles followed
- [x] File size guidelines met
- [x] Functions ≤30 lines
- [x] No circular dependencies
- [x] Type hints everywhere
- [x] Documentation complete
- [x] Phase 3 data layer modular architecture completed
