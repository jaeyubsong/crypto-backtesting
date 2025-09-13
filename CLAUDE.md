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

**Run before EVERY commit:**
```bash
uv run pytest  # All tests must pass
uv run ruff check --fix  # Fix linting issues
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

### 6. Testing Standards

**Test Organization:**
```
tests/
├── unit/          # Unit tests (isolated, mocked dependencies)
├── integration/   # Integration tests (real dependencies)
├── e2e/          # End-to-end tests (full workflow)
└── fixtures/     # Shared test data and utilities
```

**Test Naming:**
```python
def test_should_[expected_behavior]_when_[condition]():
    # Arrange
    # Act
    # Assert
```

**Coverage Guidelines:**
- Minimum overall coverage: 80%
- Core business logic: 90%+
- API endpoints: 85%+
- Helper/utility functions: Covered through usage
- Data models/DTOs: No direct tests needed
- Configuration classes: No tests needed

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
- **Run tests**: `uv run pytest`
- **Run specific test**: `uv run pytest tests/test_file.py::test_function -v`
- **Run tests with coverage**: `uv run pytest --cov`
- **Run tests in watch mode**: `uv run pytest-watch`
- **Run pre-commit on all files**: `uv run pre-commit run --all-files`

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

- [ ] Tests written FIRST for business logic (TDD)
- [ ] All tests passing
- [ ] Code coverage >= 80% overall
- [ ] No linting errors
- [ ] SOLID principles followed
- [ ] All files follow size guidelines (target ≤ 200 lines, max 300 without exception approval)
- [ ] No functions > 30 lines
- [ ] No circular dependencies
- [ ] Type hints on all functions
- [ ] Docstrings on all public APIs
- [ ] Committed frequently with clear messages

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
