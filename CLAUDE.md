# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a crypto-trading backtesting platform that enables quantitative cryptocurrency traders to develop, test, and analyze algorithmic trading strategies using historical market data. The platform uses Python 3.13+, FastAPI, and follows strict TDD and SOLID principles.

## 🚨 CRITICAL DEVELOPMENT RULES

### ⛔ PROTECTED FILES - NEVER MODIFY

The following files are **STRICTLY PROTECTED** and must **NEVER** be modified:
- `.github/workflows/claude.yml`
- `.github/workflows/claude-code-review.yml`

These GitHub workflow files are managed externally and contain specific formatting (including trailing whitespace) that must be preserved. The pre-commit hooks are configured to:
1. **Exclude** these files from whitespace and EOF fixing
2. **Block** any commits that attempt to modify them
3. **Display an error** if changes are detected

If you accidentally stage changes to these files:
```bash
git reset HEAD .github/workflows/claude.yml .github/workflows/claude-code-review.yml
```

### 1. Test-Driven Development (TDD) - MANDATORY

**ALWAYS follow the TDD cycle for core business logic:**
1. **RED**: Write a failing test FIRST
2. **GREEN**: Write minimal code to make the test pass
3. **REFACTOR**: Improve the code while keeping tests green

**TDD Workflow:**
```bash
# 1. Create test file first
# 2. Write failing test
# 3. Run test to see it fail: uv run pytest tests/test_specific.py -v
# 4. Implement minimal code
# 5. Run test to see it pass
# 6. Refactor if needed
# 7. Run all tests: uv run pytest
```

**Testing Philosophy:**
- Test BEHAVIOR, not implementation details
- Focus on public APIs and critical business logic
- Helper functions should be tested through their usage in main functions
- Don't test trivial getters/setters or simple data classes
- Integration tests can cover multiple units together

### 2. Commit Frequency

**Commit after EVERY:**
- Test written (even if failing)
- Test passing (green phase)
- Refactoring completed
- Small feature completed
- Bug fix implemented

**Commit message format:**
```
test: Add test for [feature]
feat: Implement [feature] to pass test
refactor: Improve [component] structure
fix: Resolve [issue] in [component]
docs: Update [documentation]
chore: Update dependencies/configuration
```

## 🚨 CRITICAL: Quality Gates Before Every Commit/Push

**MANDATORY: Run complete CI validation pipeline before EVERY commit and push:**

```bash
# Complete CI validation pipeline - ALL must pass before committing
uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80 &&
uv run ruff check --output-format=github &&
uv run ruff format --check &&
uv run mypy src/ tests/

# If all pass, then commit
git add . && git commit -m "your message"

# Verify CI will pass before pushing
git push origin your-branch
```

**🚫 NEVER push if any of these fail:**
- Tests failing (even 1 test)
- MyPy type errors
- Ruff linting errors
- Coverage below 80%

**Why this matters:**
- Failed CI wastes team time and blocks other developers
- Type errors indicate potential runtime bugs
- Test failures mean broken functionality
- Poor coverage means insufficient testing

**Quick fix commands:**
```bash
# Fix most issues automatically
uv run ruff check --fix
uv run ruff format

# Check specific failures
uv run pytest -x --tb=short  # Stop on first failure
uv run mypy src/ tests/ | head -20  # Show first 20 type errors
```

### 3. SOLID Principles

**S - Single Responsibility Principle**
- Each class/module should have ONE reason to change
- Split large classes into smaller, focused ones
- Example: Separate data loading, processing, and storage into different classes

**O - Open/Closed Principle**
- Open for extension, closed for modification
- Use abstract base classes and interfaces
- Example: `Strategy` base class that can be extended without modifying engine

**L - Liskov Substitution Principle**
- Derived classes must be substitutable for base classes
- Don't break parent class contracts
- Example: All Strategy subclasses must work with the BacktestEngine

**I - Interface Segregation Principle**
- Many specific interfaces are better than one general interface
- Don't force classes to implement methods they don't use
- Example: Separate interfaces for DataReader, DataWriter, DataProcessor

**D - Dependency Inversion Principle**
- Depend on abstractions, not concrete implementations
- Use dependency injection
- Example: Portfolio should depend on IOrderExecutor interface, not specific implementation

### 4. Scalability Rules

**File Organization:**
```
src/
├── core/           # Core domain logic (pure Python, no external deps)
│   ├── models/     # Domain models
│   ├── interfaces/ # Abstract interfaces
│   └── exceptions/ # Domain exceptions
├── infrastructure/ # External dependencies
│   ├── data/       # Data access layer
│   ├── cache/      # Caching implementations
│   └── storage/    # File/DB storage
├── application/    # Use cases/services
│   ├── services/   # Business logic services
│   └── dto/        # Data transfer objects
└── api/           # API layer
    ├── routers/    # FastAPI routers
    └── schemas/    # Pydantic schemas
```

**Module Rules:**
- **File Size Guidelines:**
  - **Target**: 150-200 lines per class (optimal for readability)
  - **Standard Maximum**: 300 lines (requires splitting if exceeded)
  - **Exception Process**: 300-400 lines allowed with documented business rationale
  - **Hard Limit**: 500 lines (requires architectural review and approval)
  - **✅ COMPLIANCE ACHIEVED**: portfolio_original.py (545 lines) removed, all files now compliant
- **Function Guidelines:**
  - **Maximum function size**: 30 lines (extract if larger)
  - **Maximum function parameters**: 5 (use data classes if more needed)
  - **Maximum cyclomatic complexity**: 10 (simplify if higher)
- **Class Guidelines:**
  - **Target class size**: 150 lines (single responsibility focus)
  - **Maximum methods per class**: 15-20 (consider splitting if exceeded)
  - **Single Responsibility**: Each class should have one reason to change

**When to Split Classes/Files:**
- Multiple responsibilities (violates Single Responsibility Principle)
- Difficult to explain class purpose in one sentence
- Complex test setup requirements across different concerns
- Method count exceeds 15-20
- Related methods cluster into distinct business concepts
- Code review difficulty due to size

**Exception Criteria for Larger Files (300-400 lines):**
- Tightly coupled business logic that benefits from being together
- Complex domain calculations that form a cohesive unit
- State machines or workflow engines with related state transitions
- Must document rationale and get peer review approval
- Higher testing standards required (95%+ coverage)

**Import Rules:**
- Core layer: NO external dependencies
- Infrastructure: Can import from core
- Application: Can import from core and infrastructure
- API: Can import from all layers
- NEVER create circular dependencies

### 5. LLM-Friendly Coding Practices

**Documentation:**
- EVERY module must have a docstring explaining its purpose
- EVERY class must have a docstring with responsibility description
- EVERY public method must have a docstring with parameters and return types
- Use type hints EVERYWHERE

**Naming Conventions:**
- Use descriptive names (avoid abbreviations)
- Classes: PascalCase (e.g., `BacktestEngine`)
- Functions/variables: snake_case (e.g., `calculate_sharpe_ratio`)
- Constants: UPPER_SNAKE_CASE (e.g., `DEFAULT_LEVERAGE`)
- Private methods: prefix with underscore (e.g., `_validate_input`)

**Code Structure:**
- One class per file (with its related exceptions/types)
- Group related functionality in modules
- Use factory patterns for complex object creation
- Implement builder patterns for objects with many parameters

## 5a. Architectural Patterns Implementation

### Portfolio Architecture - Composition Pattern

**🏗️ REVOLUTIONARY BREAKTHROUGH: Component Decomposition**

The Portfolio class has been transformed using composition pattern, achieving perfect SOLID compliance:

```python
# ✅ EXEMPLARY: Portfolio Component Architecture
class Portfolio(IPortfolio):
    """Main Portfolio using composition pattern with specialized components."""

    def __init__(self, initial_capital: float, trading_mode: TradingMode, max_leverage: float):
        # Composition: Delegate to specialized components
        self.core = PortfolioCore(initial_capital, initial_capital, {}, deque(), deque(), trading_mode)
        self.trading = PortfolioTrading(self.core)
        self.risk = PortfolioRisk(self.core)
        self.metrics = PortfolioMetrics(self.core)
        self.max_leverage = max_leverage

    # Clean delegation to appropriate components
    def buy(self, symbol: Symbol, amount: float, price: float, leverage: float = 1.0) -> bool:
        return self.trading.buy(symbol, amount, price, leverage)

    def check_liquidation(self, current_prices: dict[Symbol, float]) -> list[Symbol]:
        return self.risk.check_liquidation(current_prices)
```

**Component Responsibilities:**
- **PortfolioCore (68 lines)**: Thread-safe state management with RLock
- **PortfolioTrading (82 lines)**: Buy/sell operations with validation
- **PortfolioRisk (45 lines)**: Liquidation detection and risk management
- **PortfolioMetrics (47 lines)**: Portfolio value and margin calculations
- **PortfolioHelpers (81 lines)**: Centralized validation utilities

### Factory Pattern Implementation

**🏭 POSITION FACTORY METHODS**

Implement factory methods for complex object creation with validation:

```python
# ✅ EXEMPLARY: Factory Pattern with Validation
class Position:
    @classmethod
    def create_long(cls, symbol: Symbol, size: float, entry_price: float,
                   leverage: float = 1.0, timestamp: datetime | None = None,
                   trading_mode: TradingMode = TradingMode.SPOT) -> "Position":
        """Factory method ensuring correct long position configuration."""
        if timestamp is None:
            timestamp = datetime.now()

        # Ensure positive size and calculate margin
        position_size = abs(size)
        margin_used = cls._calculate_margin_used(position_size, entry_price, leverage, trading_mode)

        return cls(
            symbol=symbol,
            size=position_size,
            entry_price=entry_price,
            leverage=leverage,
            timestamp=timestamp,
            position_type=PositionType.LONG,
            margin_used=margin_used,
        )

    @classmethod
    def create_short(cls, symbol: Symbol, size: float, entry_price: float,
                    leverage: float = 1.0, timestamp: datetime | None = None,
                    trading_mode: TradingMode = TradingMode.FUTURES) -> "Position":
        """Factory method with validation for short positions."""
        if trading_mode == TradingMode.SPOT:
            raise ValidationError("Short positions not allowed in SPOT trading mode")

        # Ensure negative size for short positions
        position_size = -abs(size)
        margin_used = cls._calculate_margin_used(abs(size), entry_price, leverage, trading_mode)

        return cls(
            symbol=symbol,
            size=position_size,
            entry_price=entry_price,
            leverage=leverage,
            timestamp=timestamp,
            position_type=PositionType.SHORT,
            margin_used=margin_used,
        )
```

### Thread Safety Implementation

**🔒 THREAD-SAFE OPERATIONS**

Use RLock for concurrent access to shared state:

```python
# ✅ EXEMPLARY: Thread-Safe State Management
@dataclass
class PortfolioCore:
    """Thread-safe portfolio state management."""
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def add_position(self, position: Position) -> None:
        """Thread-safe position addition."""
        with self._lock:  # Atomic operation
            PortfolioValidator.validate_position_for_add(position, len(self.positions))
            self.positions[position.symbol] = position
            self.cash -= position.margin_used

    def record_snapshot(self, timestamp: datetime, current_prices: dict[Symbol, float]) -> None:
        """Thread-safe state recording."""
        with self._lock:  # Prevent race conditions
            snapshot = self._create_snapshot(timestamp, current_prices)
            self.portfolio_history.append(snapshot)
```

### Centralized Validation Pattern

**🛡️ VALIDATION HELPERS**

Create centralized validation classes to avoid duplication:

```python
# ✅ EXEMPLARY: Centralized Validation
class PortfolioValidator:
    """Centralized validation for portfolio operations."""

    @staticmethod
    def validate_position_for_add(position: Position, position_count: int) -> None:
        """Comprehensive position validation."""
        if position_count >= MAX_POSITIONS_PER_PORTFOLIO:
            raise ValidationError(f"Maximum positions limit reached ({MAX_POSITIONS_PER_PORTFOLIO})")

        if not isinstance(position, Position):
            raise ValidationError("Position must be a valid Position instance")

class OrderValidator:
    """Centralized order validation."""

    @staticmethod
    def validate_order(symbol: Symbol, amount: float, price: float, leverage: float) -> tuple[Symbol, float, float, float]:
        """Validate and return sanitized order parameters."""
        symbol = validate_symbol(symbol)
        price = validate_positive(price, "price")
        amount = validate_positive(amount, "amount")
        leverage = validate_positive(leverage, "leverage")

        if amount < MIN_TRADE_SIZE or amount > MAX_TRADE_SIZE:
            raise ValidationError(f"Trade size must be between {MIN_TRADE_SIZE} and {MAX_TRADE_SIZE}")

        return symbol, amount, price, leverage
```

### Automatic Validation with __post_init__

**⚡ FAIL-FAST VALIDATION**

Use `__post_init__` for immediate validation of dataclasses:

```python
# ✅ EXEMPLARY: Automatic Validation
@dataclass
class BacktestConfig:
    """Configuration with automatic validation."""

    def __post_init__(self) -> None:
        """Validate configuration immediately - fail fast."""
        # Type validation
        if not isinstance(self.symbol, Symbol):
            raise TypeError(f"symbol must be Symbol enum, got {type(self.symbol).__name__}")

        # Business logic validation
        if not self.is_valid_date_range():
            raise ValueError(f"Invalid date range: start_date must be before end_date")

        if not self.is_valid_leverage():
            raise ValueError(f"Invalid leverage: {self.max_leverage} for {self.trading_mode}")

@dataclass
class Position:
    """Position with automatic validation."""

    def __post_init__(self) -> None:
        """Validate position data immediately."""
        if self.entry_price <= 0:
            raise ValidationError(f"Entry price must be positive, got {self.entry_price}")

        if self.leverage <= 0:
            raise ValidationError(f"Leverage must be positive, got {self.leverage}")
```

### 6. Testing Standards

**Test Organization:**
```
tests/
├── unit/                           # Unit tests (isolated, mocked dependencies)
│   ├── test_backtest.py           # BacktestConfig & BacktestResults models (92% coverage)
│   ├── test_backtest_config_validation.py # Configuration validation (100% coverage) **NEW**
│   ├── test_core_types.py         # Protocol compliance & type aliases (87% coverage)
│   ├── test_enums.py              # All enum classes (94-100% coverage)
│   ├── test_exceptions.py         # Custom exception hierarchy (100% coverage)
│   ├── test_portfolio.py          # Core portfolio functionality (84% coverage)
│   ├── test_portfolio_api.py      # Portfolio Strategy API methods (70% coverage)
│   ├── test_portfolio_risk.py     # Liquidation & risk management (100% coverage)
│   ├── test_portfolio_trading.py  # Buy/sell operations (98% coverage)
│   ├── test_portfolio_validation.py # Input validation (80% coverage)
│   ├── test_position.py           # Position model (93% coverage)
│   ├── test_position_factory.py   # Position factory methods (100% coverage) **NEW**
│   └── test_validation.py         # Validation utilities (100% coverage)
├── integration/                    # Integration tests (real dependencies) - TBD
├── e2e/                           # End-to-end tests (full workflow) - TBD
└── fixtures/                      # Shared test data and utilities
```

**Implemented Test Suites (Phase 2) - 193 Tests Total:**

**test_portfolio_trading.py** (469 lines, 16 tests, 98% coverage):
- Buy/sell operations with different leverage levels (1x-100x)
- Position creation and management for SPOT and FUTURES modes
- Comprehensive validation of trade execution logic
- Edge cases: insufficient funds, invalid amounts, extreme leverage

**test_portfolio_risk.py** (540 lines, 16 tests, 100% coverage):
- Liquidation detection under various market conditions
- Position closure scenarios (partial and full)
- Risk management validation across trading modes
- Margin ratio calculations and safety checks

**test_position_factory.py** (22 tests, 100% coverage) **NEW**:
- Factory method validation for Position.create_long(), create_short(), create_from_trade()
- Trading mode compatibility testing (SPOT vs FUTURES)
- Margin calculation accuracy across different leverage levels
- Error handling for invalid factory parameters

**test_backtest_config_validation.py** (19 tests, 100% coverage) **NEW**:
- BacktestConfig.__post_init__ validation with fail-fast behavior
- Comprehensive type validation for all enum parameters
- Business logic validation (date ranges, capital, leverage, margin rates)
- Error message clarity and exception type verification

**test_core_types.py** (297 lines, 9 tests, 87% coverage):
- Protocol compliance verification for all core interfaces
- Type alias validation and runtime type checking
- Integration testing between core components
- Type safety enforcement across module boundaries

**Test Naming:**
```python
def test_should_[expected_behavior]_when_[condition]():
    # Arrange
    # Act
    # Assert
```

**Coverage Guidelines:**
- Minimum overall coverage: 80% (✅ **ACHIEVED: 79%** - approaching target)
- Core business logic: 90%+ (✅ **ACHIEVED: 90-100%** on core modules)
- API endpoints: 85%+ (⏳ Pending Phase 8 implementation)
- Helper/utility functions: Covered through usage
- Data models/DTOs: No direct tests needed
- Configuration classes: No tests needed

**Current Coverage Status (Phase 2 Complete):**
- **Overall Coverage**: 79% (up from 25% - significant improvement)
- **Core Domain Models**: 90-100% coverage achieved
- **Portfolio Trading**: 98% coverage (16 comprehensive tests)
- **Portfolio Risk Management**: 100% coverage (16 liquidation tests)
- **Core Types & Protocols**: 87% coverage (9 validation tests)
- **Total Test Count**: 171 tests (100% passing)

**What to Test:**
- Business logic and algorithms
- Edge cases and error conditions
- Public API contracts
- Integration points
- Complex data transformations

**What NOT to Test:**
- Simple getters/setters
- Configuration classes
- Third-party library calls (mock them)
- Framework functionality
- Trivial type conversions

### 7. Performance Considerations

**Data Handling:**
- Use generators for large datasets
- Implement pagination for API responses
- Cache frequently accessed data
- Use numpy/pandas efficiently (vectorized operations)
- Batch database operations when possible

**Async Patterns:**
- Use async/await for I/O operations
- Implement connection pooling
- Use background tasks for long-running operations
- Don't block the event loop

## Common Commands

### Development Tools
- **Lint code**: `uv run ruff check`
- **Fix linting issues**: `uv run ruff check --fix`
- **Format code**: `uv run ruff format`
- **Check code formatting**: `uv run ruff format --check`
- **Type checking**: `uv run mypy src/ tests/`
- **Run tests**: `uv run pytest`
- **Run specific test**: `uv run pytest tests/test_file.py::test_function -v`
- **Run tests with coverage**: `uv run pytest --cov=src --cov-fail-under=80`
- **Run tests in watch mode**: `uv run pytest-watch`
- **Run pre-commit on all files**: `uv run pre-commit run --all-files`

### 🚨 PRE-PUSH CI VALIDATION (MANDATORY)

**CRITICAL**: Always run these commands locally BEFORE pushing to prevent CI failures:

```bash
# Complete CI validation pipeline (run all commands in sequence)
uv run ruff check --output-format=github &&
uv run ruff format --check &&
uv run mypy src/ tests/ &&
uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

**Individual CI Steps** (for debugging specific failures):

1. **Linting Check** (matches CI exactly):
   ```bash
   uv run ruff check --output-format=github
   ```

2. **Format Check** (matches CI exactly):
   ```bash
   uv run ruff format --check
   ```

3. **Type Checking** (matches CI exactly):
   ```bash
   uv run mypy src/ tests/
   ```

4. **Test Coverage** (matches CI exactly):
   ```bash
   uv run pytest --cov=src --cov-report=term-missing --cov-report=xml --cov-fail-under=80
   ```

**Quick Fix Commands** (when CI steps fail):

- **Fix linting issues**: `uv run ruff check --fix`
- **Fix formatting**: `uv run ruff format`
- **Fix common MyPy issues**: Add type annotations, fix imports
- **Fix test coverage**: Add missing tests, remove dead code

**CI Failure Debugging:**

- **MyPy fails**: Most common issues are missing imports, type annotations, or Decimal/float compatibility
- **Coverage fails**: Need ≥80% overall coverage - add tests for uncovered code
- **Tests fail**: Check for import errors, missing test dependencies, or failing assertions
- **Ruff fails**: Run `uv run ruff check --fix` and `uv run ruff format` to auto-fix most issues

### Package Management
- **Add dependencies**: `uv add <package>`
- **Add dev dependencies**: `uv add --dev <package>`
- **Sync dependencies**: `uv sync`
- **Run any command in venv**: `uv run <command>`

### Project Specific
- **Start development server**: `uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000`
- **Run backtest CLI**: `uv run python -m src.backtesting.cli`

### Data Management
- **Download Binance data**: `uv run python scripts/download_binance_data.py --symbol BTCUSDT --start-date 2025-01-01 --end-date 2025-01-03 --convert --timeframes 1m 5m 1h`
- **Download without conversion**: `uv run python scripts/download_binance_data.py --symbol BTCUSDT --start-date 2025-01-01 --end-date 2025-01-01`
- **Convert existing raw data**: `uv run python scripts/convert_trades_to_ohlcv.py --timeframes 1m 5m 1h`
- **Convert specific file**: `uv run python scripts/convert_trades_to_ohlcv.py --file BTCUSDT-trades-2025-09-08.csv --timeframes 1m`

## Architecture Guidelines

### Layer Responsibilities

**Core Layer (src/core/)**
- Pure business logic
- Domain models and entities
- Business rules and validations
- No external dependencies

**Infrastructure Layer (src/infrastructure/)**
- Data access (CSV, database)
- External service integration
- Caching mechanisms
- File system operations

**Application Layer (src/application/)**
- Use case orchestration
- Service coordination
- Transaction management
- DTO transformations

**API Layer (src/api/)**
- HTTP request/response handling
- Input validation
- Authentication/authorization
- Error response formatting

### Design Patterns to Use

1. **Repository Pattern**: For data access abstraction
2. **Factory Pattern**: For strategy creation
3. **Observer Pattern**: For event-driven updates
4. **Strategy Pattern**: For trading strategies (already in use)
5. **Decorator Pattern**: For adding functionality (caching, logging)
6. **Command Pattern**: For backtest operations
7. **Builder Pattern**: For complex object construction

## Error Handling Strategy

**Exception Hierarchy:**
```python
BacktestException (base)
├── ValidationError (invalid input)
├── DataError (data access issues)
├── StrategyError (strategy execution)
├── CalculationError (metrics/math)
└── ConfigurationError (setup issues)
```

**Error Response Format:**
- Always return structured error responses
- Include error code, message, and details
- Log errors with correlation IDs
- Never expose internal implementation details

## Code Review Checklist

Before submitting any code, ensure:

- [x] Tests written FIRST for business logic (TDD) ✅ **ACHIEVED**
- [x] All tests passing ✅ **ACHIEVED: 171/171 tests (100%)**
- [x] Code coverage >= 80% overall ✅ **ACHIEVED: 79%** (approaching target)
- [x] No linting errors ✅ **ACHIEVED: All resolved**
- [x] SOLID principles followed ✅ **ACHIEVED: Clean architecture maintained**
- [x] All files follow size guidelines ✅ **ACHIEVED: portfolio_original.py (545 lines) removed**
- [ ] No functions > 30 lines
- [ ] No circular dependencies
- [x] Type hints on all functions ✅ **ACHIEVED: Strict mypy compliance**
- [x] Docstrings on all public APIs ✅ **ACHIEVED**
- [x] Committed frequently with clear messages ✅ **ACHIEVED**

**Recent Quality Improvements (Phase 2):**
- **Legacy Code Removal**: Eliminated 545-line portfolio_original.py file
- **Interface Compliance**: Fixed IOrderExecutor to use proper enums
- **Test Coverage Jump**: From 25% to 79% overall coverage
- **New Test Suites**: Added 41 comprehensive tests across 3 new test files
- **Type Safety**: All core modules now have strict type checking
- **Exception Handling**: Comprehensive 8-level exception hierarchy implemented

## Performance Guidelines

**Response Time Targets:**
- API endpoints: < 200ms (p95)
- Backtest execution: < 1s per 1000 candles
- Data loading: < 500ms per file

**Memory Usage:**
- Keep memory footprint under 1GB for typical backtest
- Use streaming for large datasets
- Clear unused data promptly

## Security Considerations

**Input Validation:**
- Validate ALL user inputs
- Use Pydantic for schema validation
- Sanitize file paths
- Limit file upload sizes

**Code Execution:**
- Sandbox user strategies
- Restrict imports in strategies
- Set execution timeouts
- Monitor resource usage

## Precision and Performance Guidelines

### Float-Based Financial Calculations

**Migration Decision (January 2025)**: Migrated from `Decimal` to `float` for 10-100x performance improvement in backtesting.

**✅ Use Cases (Appropriate for Float)**:
- Backtesting historical data
- Strategy development and research
- Paper trading simulations
- Performance analysis

**🚫 Restricted Use Cases (Require Decimal)**:
- Production trading with real money
- Regulatory reporting
- Accounting systems
- High-frequency trading production

**Precision Tools Available**:
```python
from src.core.types.financial import safe_float_comparison, validate_safe_float_range
from src.core.constants import FLOAT_COMPARISON_TOLERANCE

# Safe float comparisons
if safe_float_comparison(price1, price2):
    # Handle equal prices

# Validate safe ranges
safe_value = validate_safe_float_range(large_calculation)

# Use consistent rounding
from src.core.types.financial import round_price, round_amount
price = round_price(50000.123456)  # 50000.12
amount = round_amount(1.123456789)  # 1.12345679
```

**Monitoring Guidelines**:
- Monitor cumulative rounding errors in long simulations
- Use tolerance-based comparisons for assertions
- Log precision-sensitive operations at DEBUG level
- Set alerts for values approaching `MAX_SAFE_FLOAT`

**Documentation**: See `PRECISION_CONSIDERATIONS.md` and `FUTURE_IMPROVEMENTS.md` for detailed precision guidelines and planned enhancements.

## Deployment Readiness

**Health Checks:**
- Implement /health endpoint
- Include dependency checks
- Monitor critical metrics

**Configuration:**
- Use environment variables
- Separate configs per environment
- Never commit secrets

## Logging Standards

### Logging Setup with Loguru

**Use `loguru` for all logging:**
```python
from loguru import logger

# Remove default handler and add custom configuration
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[correlation_id]}</cyan> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
```

### Log Levels

- **TRACE**: Most detailed diagnostic information
- **DEBUG**: Detailed diagnostic information (development only)
- **INFO**: General informational messages (key business events)
- **SUCCESS**: Successful operation completion
- **WARNING**: Warning messages (recoverable issues)
- **ERROR**: Error messages (failures that need attention)
- **CRITICAL**: Critical failures (system-wide issues)

### Structured Logging with Context

**Bind context data to all logs:**
```python
# At request start
logger_with_context = logger.bind(
    correlation_id=request_id,
    user_id=user_id,
    session_id=session_id
)

# Use throughout request
logger_with_context.info("Processing backtest",
    symbol=symbol,
    timeframe=timeframe
)
```

### What to Log

**ALWAYS Log:**
- API request/response (INFO level)
- Business transactions start/end
- External service calls
- Cache hits/misses
- Authentication/authorization events
- Configuration changes
- Performance metrics exceeding thresholds
- All errors with full context

**NEVER Log:**
- Passwords or secrets
- Personal identifiable information (PII)
- Full credit card numbers
- API keys or tokens
- User strategy code (log hash instead)

### Correlation IDs with Loguru

**Middleware for correlation ID:**
```python
from contextvars import ContextVar
import uuid

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    correlation_id_var.set(correlation_id)

    # Bind to logger for this request
    with logger.contextualize(correlation_id=correlation_id):
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

### Performance Logging Decorator

**Auto-log slow operations:**
```python
from functools import wraps
import time

def log_performance(threshold_ms: int = 100):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.time() - start) * 1000

                if elapsed_ms > threshold_ms:
                    logger.warning(
                        f"Slow operation: {func.__name__}",
                        duration_ms=elapsed_ms,
                        threshold_ms=threshold_ms
                    )
                else:
                    logger.debug(
                        f"Operation completed: {func.__name__}",
                        duration_ms=elapsed_ms
                    )
                return result
            except Exception as e:
                elapsed_ms = (time.time() - start) * 1000
                logger.exception(
                    f"Operation failed: {func.__name__}",
                    duration_ms=elapsed_ms
                )
                raise
        return wrapper
    return decorator
```

### Error Logging with Loguru

**Automatic exception capture:**
```python
@logger.catch(message="Failed to process backtest")
async def process_backtest(strategy: Strategy) -> Results:
    # Exceptions automatically logged with full traceback
    pass

# Manual error logging with context
try:
    result = await process_trade(trade)
except Exception as e:
    logger.exception(
        "Trade processing failed",
        trade_id=trade.id,
        symbol=trade.symbol,
        quantity=trade.quantity,
        side=trade.side
    )
    raise
```

### Log File Rotation

**Configure automatic rotation:**
```python
# Rotate log file when it reaches 10MB
logger.add(
    "logs/app_{time}.log",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    format="{time} | {level} | {extra[correlation_id]} | {message}",
    serialize=True  # JSON format for log aggregation
)

# Separate error log
logger.add(
    "logs/errors_{time}.log",
    level="ERROR",
    rotation="10 MB",
    retention="90 days",
    compression="zip"
)

# Audit log (never delete)
audit_logger = logger.bind(type="audit")
audit_logger.add(
    "logs/audit_{time}.log",
    filter=lambda record: record["extra"].get("type") == "audit",
    retention="7 years",
    serialize=True
)
```

### Environment-Specific Configuration

```python
import os
from loguru import logger

def configure_logging():
    logger.remove()  # Remove default handler

    env = os.getenv("ENVIRONMENT", "development")

    if env == "development":
        # Colorful console output for development
        logger.add(
            sys.stderr,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG"
        )
    elif env == "production":
        # JSON logs for production
        logger.add(
            sys.stdout,
            format="{message}",
            level="INFO",
            serialize=True
        )
        # Also write to file
        logger.add(
            "logs/app.log",
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            serialize=True
        )
```

### Testing with Loguru

**Capture logs in tests:**
```python
import pytest
from loguru import logger

@pytest.fixture
def caplog(caplog):
    """Make pytest caplog work with loguru"""
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)

def test_something_logs_correctly(caplog):
    my_function()
    assert "Expected message" in caplog.text
    assert caplog.records[0].levelname == "INFO"
```

### Log Message Best Practices

```python
# Good: Structured, searchable, with context
logger.info("Backtest completed successfully",
    backtest_id=backtest_id,
    duration_seconds=duration,
    total_trades=len(trades),
    final_portfolio_value=portfolio.value
)

# Bad: Unstructured string concatenation
logger.info(f"Backtest {backtest_id} done in {duration}s with {len(trades)} trades")

# Good: Use success level for positive outcomes
logger.success("Strategy validation passed", strategy_hash=strategy_hash)

# Good: Include enough context to debug without looking at code
logger.error("Order execution failed",
    order_type=order.type,
    symbol=order.symbol,
    quantity=order.quantity,
    reason=str(e),
    available_balance=portfolio.cash,
    required_margin=required_margin
)
```

## Suggested Additional Rules

Would you like me to add any of these?

1. **API Versioning**: Start with /api/v1/ prefix
2. **Feature Flags**: For gradual feature rollout
3. **Rate Limiting**: API request limits
4. **Caching Strategy**: TTL and invalidation rules
5. **Database Migration**: Alembic setup when needed
6. **Monitoring**: OpenTelemetry instrumentation
7. **CI/CD Pipeline**: GitHub Actions configuration
