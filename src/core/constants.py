"""
Core constants and limits.

Defines system-wide constants and resource limits to prevent abuse
and ensure system stability.
"""

# Portfolio Limits
MAX_POSITIONS_PER_PORTFOLIO = 100  # Maximum number of open positions
MAX_TRADES_HISTORY = 10000  # Maximum trades to keep in history
MAX_PORTFOLIO_HISTORY = 5000  # Maximum portfolio snapshots to keep

# Trading Limits
MIN_TRADE_SIZE = 0.00001  # Minimum trade size (prevents dust trades)
MAX_TRADE_SIZE = 1000000  # Maximum single trade size

# Leverage Limits (by trading mode)
MAX_LEVERAGE_SPOT = 1.0
MAX_LEVERAGE_FUTURES = 125.0
MAX_LEVERAGE_MARGIN = 10.0

# Risk Management
MAINTENANCE_MARGIN_RATE_DEFAULT = 0.005  # 0.5% default
MARGIN_CALL_THRESHOLD = 0.5  # 50% margin ratio triggers margin call
LIQUIDATION_THRESHOLD = 0.25  # 25% margin ratio triggers liquidation

# Circuit Breakers
MAX_DAILY_LOSS_PERCENT = 50.0  # Stop trading if 50% loss in a day
MAX_CONSECUTIVE_LOSSES = 10  # Stop after 10 consecutive losing trades
MAX_DRAWDOWN_PERCENT = 75.0  # Stop if 75% drawdown from peak

# Fee Constants
DEFAULT_MAKER_FEE = 0.001  # 0.1% maker fee
DEFAULT_TAKER_FEE = 0.001  # 0.1% taker fee
FUTURES_MAKER_FEE = 0.0002  # 0.02% futures maker
FUTURES_TAKER_FEE = 0.0006  # 0.06% futures taker

# System Limits
MAX_BACKTEST_DURATION_DAYS = 3650  # 10 years maximum backtest
MIN_INITIAL_CAPITAL = 100.0  # Minimum starting capital
MAX_INITIAL_CAPITAL = 100000000.0  # Maximum starting capital (100M)
