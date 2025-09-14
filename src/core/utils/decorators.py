"""
Utility decorators for input validation and common functionality.
"""

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from src.core.exceptions.backtest import ValidationError
from src.core.utils.validation import validate_positive, validate_symbol

F = TypeVar("F", bound=Callable[..., Any])


def validate_inputs(func: F) -> F:
    """Decorator to automatically validate common trading inputs.

    Validates:
    - symbol: Must be Symbol enum
    - amount/size: Must be positive
    - price: Must be positive
    - leverage: Must be positive

    Usage:
        @validate_inputs
        def buy(self, symbol: Symbol, amount: float, price: float) -> bool:
            # Validation handled automatically
            ...

    Raises:
        ValidationError: If any input is invalid
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Get function signature to map arguments
        import inspect

        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Validate each argument based on name and type
        for param_name, value in bound_args.arguments.items():
            if param_name == "self":
                continue

            if param_name == "symbol" and value is not None:
                try:
                    bound_args.arguments[param_name] = validate_symbol(value)
                except (TypeError, ValueError) as e:
                    raise ValidationError(f"Invalid {param_name}: {e}") from e

            elif (
                param_name in ["amount", "size", "quantity"]
                and value is not None
                or param_name == "price"
                and value is not None
                or param_name == "leverage"
                and value is not None
            ):
                try:
                    bound_args.arguments[param_name] = validate_positive(value, param_name)
                except (TypeError, ValueError) as e:
                    raise ValidationError(f"Invalid {param_name}: {e}") from e

        return func(*bound_args.args, **bound_args.kwargs)

    return wrapper  # type: ignore


def log_trades(func: F) -> F:
    """Decorator to automatically log trading operations with structured context.

    Logs entry and exit of trading functions with correlation IDs and
    comprehensive trading context for better observability.

    Usage:
        @log_trades
        def buy(self, symbol: Symbol, amount: float, price: float) -> bool:
            # Logging handled automatically with correlation ID
            ...
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Import here to avoid circular imports
        import uuid

        from loguru import logger

        # Generate correlation ID for request tracing
        correlation_id = str(uuid.uuid4())[:8]

        # Extract trading context from arguments
        func_name = func.__name__
        context = {"correlation_id": correlation_id}

        # Get function signature to extract meaningful parameters
        import inspect

        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Extract relevant trading parameters with proper serialization
        for param_name, value in bound_args.arguments.items():
            if param_name == "self":
                continue
            if param_name in ["symbol", "amount", "size", "price", "leverage", "percentage"]:
                # Handle enum values (like Symbol) by extracting their value
                if hasattr(value, "value"):
                    context[param_name] = str(value.value)
                # Handle Decimal types by converting to string for JSON serialization
                elif hasattr(value, "quantize"):
                    context[param_name] = str(value)
                else:
                    context[param_name] = value

        # Add timestamp for precise timing
        import time

        start_time = time.time()
        context["timestamp"] = str(time.time())

        # Log function entry with structured context
        logger.info(f"Trading operation started: {func_name}", extra=context)

        try:
            result = func(*args, **kwargs)

            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000

            # Log successful completion with result context
            success_context = {
                **context,
                "success": True,
                "execution_time_ms": round(execution_time_ms, 2),
                "result_type": type(result).__name__,
            }

            # Include result details if it's a simple type
            if isinstance(result, bool | int | float | str):
                success_context["result"] = result
            elif hasattr(result, "value") and hasattr(result, "name"):
                # Handle enum results
                success_context["result"] = result.value

            logger.success(f"Trading operation completed: {func_name}", extra=success_context)
            return result

        except Exception as e:
            # Calculate execution time even for failures
            execution_time_ms = (time.time() - start_time) * 1000

            # Log error with comprehensive context
            error_context = {
                **context,
                "success": False,
                "execution_time_ms": round(execution_time_ms, 2),
                "error_type": type(e).__name__,
                "error_message": str(e),
            }

            logger.error(f"Trading operation failed: {func_name}", extra=error_context)
            raise

    return wrapper  # type: ignore


def require_position(symbol_param: str = "symbol") -> Callable[[F], F]:
    """Decorator to ensure a position exists before executing the function.

    Args:
        symbol_param: Name of the symbol parameter in the function

    Usage:
        @require_position('symbol')
        def close_position(self, symbol: Symbol) -> bool:
            # Position existence checked automatically
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get function signature to find symbol parameter
            import inspect

            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Extract self and symbol
            self_obj = bound_args.arguments.get("self")
            symbol = bound_args.arguments.get(symbol_param)

            if (
                self_obj
                and symbol
                and hasattr(self_obj, "positions")
                and symbol not in self_obj.positions
            ):
                raise ValidationError(f"No position exists for symbol: {symbol}")

            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator
