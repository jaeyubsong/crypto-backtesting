"""
Utility decorators for input validation and common functionality.
"""

import functools
from collections.abc import Callable
from typing import Any

from src.core.exceptions.backtest import ValidationError
from src.core.utils.validation import validate_positive, validate_symbol


def _validate_trading_parameter(param_name: str, value: Any, bound_args: Any) -> None:
    """Validate a single trading parameter."""
    if param_name == "symbol" and value is not None:
        try:
            bound_args.arguments[param_name] = validate_symbol(value)
        except (TypeError, ValueError) as e:
            raise ValidationError(f"Invalid {param_name}: {e}") from e

    elif _is_numeric_trading_param(param_name, value):
        try:
            bound_args.arguments[param_name] = validate_positive(value, param_name)
        except (TypeError, ValueError) as e:
            raise ValidationError(f"Invalid {param_name}: {e}") from e


def _is_numeric_trading_param(param_name: str, value: Any) -> bool:
    """Check if parameter is a numeric trading parameter that needs validation."""
    return (
        param_name in ["amount", "size", "quantity"]
        and value is not None
        or param_name == "price"
        and value is not None
        or param_name == "leverage"
        and value is not None
    )


def _process_function_arguments(
    func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]
) -> Any:
    """Process and validate function arguments."""
    import inspect

    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()

    for param_name, value in bound_args.arguments.items():
        if param_name != "self":
            _validate_trading_parameter(param_name, value, bound_args)

    return func(*bound_args.args, **bound_args.kwargs)


def validate_inputs[F: Callable[..., Any]](func: F) -> F:
    """Decorator to validate trading inputs (symbol, amount, price, leverage)."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return _process_function_arguments(func, args, kwargs)

    return wrapper  # type: ignore


def _extract_trading_context(bound_args: Any) -> dict[str, Any]:
    """Extract trading context from function arguments."""
    context = {}
    for param_name, value in bound_args.arguments.items():
        if param_name == "self":
            continue
        if param_name in ["symbol", "amount", "size", "price", "leverage", "percentage"]:
            context[param_name] = _serialize_parameter_value(value)
    return context


def _serialize_parameter_value(value: Any) -> Any:
    """Serialize parameter value for logging."""
    if hasattr(value, "value"):
        return str(value.value)  # Handle enum values
    elif hasattr(value, "quantize"):
        return str(value)  # Handle Decimal types
    else:
        return value


def _create_success_context(
    base_context: dict[str, Any], execution_time_ms: float, result: Any
) -> dict[str, Any]:
    """Create success logging context."""
    success_context = {
        **base_context,
        "success": True,
        "execution_time_ms": round(execution_time_ms, 2),
        "result_type": type(result).__name__,
    }

    if isinstance(result, bool | int | float | str):
        success_context["result"] = result
    elif hasattr(result, "value") and hasattr(result, "name"):
        success_context["result"] = result.value

    return success_context


def _create_error_context(
    base_context: dict[str, Any], execution_time_ms: float, error: Exception
) -> dict[str, Any]:
    """Create error logging context."""
    return {
        **base_context,
        "success": False,
        "execution_time_ms": round(execution_time_ms, 2),
        "error_type": type(error).__name__,
        "error_message": str(error),
    }


def _setup_logging_context(
    func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    """Setup logging context for trading operations."""
    import inspect
    import time
    import uuid

    correlation_id = str(uuid.uuid4())[:8]
    func_name = func.__name__

    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()

    context = {
        "correlation_id": correlation_id,
        "timestamp": str(time.time()),
        **_extract_trading_context(bound_args),
    }

    return context, func_name


def _execute_with_logging(
    func: Callable[..., Any],
    context: dict[str, Any],
    func_name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Any:
    """Execute function with comprehensive logging."""
    import time

    from loguru import logger

    logger.info(f"Trading operation started: {func_name}", extra=context)
    start_time = time.time()

    try:
        result = func(*args, **kwargs)
        execution_time_ms = (time.time() - start_time) * 1000
        success_context = _create_success_context(context, execution_time_ms, result)
        logger.success(f"Trading operation completed: {func_name}", extra=success_context)
        return result
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        error_context = _create_error_context(context, execution_time_ms, e)
        logger.error(f"Trading operation failed: {func_name}", extra=error_context)
        raise


def log_trades[F: Callable[..., Any]](func: F) -> F:
    """Decorator to log trading operations with correlation IDs."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        context, func_name = _setup_logging_context(func, args, kwargs)
        return _execute_with_logging(func, context, func_name, args, kwargs)

    return wrapper  # type: ignore


def _check_position_exists(
    args: tuple[Any, ...], kwargs: dict[str, Any], symbol_param: str, func: Callable[..., Any]
) -> None:
    """Check if required position exists before function execution."""
    import inspect

    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()

    self_obj = bound_args.arguments.get("self")
    symbol = bound_args.arguments.get(symbol_param)

    if self_obj and symbol and hasattr(self_obj, "positions") and symbol not in self_obj.positions:
        raise ValidationError(f"No position exists for symbol: {symbol}")


def require_position[F: Callable[..., Any]](symbol_param: str = "symbol") -> Callable[[F], F]:
    """Decorator to ensure a position exists before executing the function."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _check_position_exists(args, kwargs, symbol_param, func)
            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator
