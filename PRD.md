# Product Requirements Document: Crypto Quant Backtesting Platform

**Version:** 1.0
**Date:** September 10, 2025

## 1. Introduction & Vision

### 1.1. Overview
This document outlines the requirements for a Python-based backtesting application designed for quantitative cryptocurrency traders. The platform will enable users to develop, test, and analyze algorithmic trading strategies using historical market data from Binance. It will provide a structured framework for strategy development, a robust backtesting engine, and a user-friendly interface with powerful data visualizations and performance metrics.

### 1.2. Problem Statement
Quantitative traders and developers need a streamlined, efficient, and reliable way to test trading hypotheses on historical crypto data. Existing solutions can be overly complex, lack customization, or provide insufficient performance analytics and visualizations. There is a need for a tool that balances a structured, easy-to-use framework with the flexibility for deep, code-based strategy customization.

### 1.3. Target Audience

- **Quantitative Analysts ("Quants")**: Professionals who need a powerful tool to rapidly prototype and validate complex trading models.
- **Retail Algorithmic Traders**: Individual traders who use code to automate their strategies and need a reliable way to test them before deploying capital.
- **Python Developers & Data Scientists**: Individuals with programming skills who are exploring algorithmic trading in the crypto space.

## 2. Goals & Objectives

### 2.1. Product Goals

- **Enable Rapid Prototyping**: Allow users to quickly write and test new trading strategies with minimal boilerplate code.
- **Provide Actionable Insights**: Offer comprehensive performance metrics and clear visualizations to help users understand their strategy's behavior and performance.
- **Ensure Reliability & Accuracy**: Build a backtesting engine that accurately simulates trade execution, including common market frictions like fees and slippage.
- **Foster Organization**: Create a structured environment where strategies, data, and backtest results are organized and easily accessible.

### 2.2. Business Goals

- **Foundation for Future Growth**: Develop a core backtesting engine that can later be extended to support live trading, machine learning model integration, and other advanced features.
- **Open-Source Community (Potential)**: Create a robust open-source tool that can attract a community of developers and quants, driving innovation and adoption.

## 3. Features & Functional Requirements

### 3.1. Core Backtesting Engine

- **Event-Driven Architecture**: The engine will process historical data tick-by-tick or bar-by-bar, feeding market data to the strategy and executing trades as signals are generated.
- **Portfolio Simulation**:
  - Manages starting capital and tracks portfolio value over time.
  - Accurately simulates buy/sell order execution for both long and short positions.
  - **Leverage Support**: Enables leveraged trading with configurable maximum leverage ratios (e.g., 1x to 100x).
  - **Margin Management**: Tracks initial margin, maintenance margin, and available margin.
  - **Liquidation Engine**: Automatically liquidates positions when margin requirements are not met.
  - Models transaction costs including:
    - Spot trading fees (e.g., Binance 0.1%)
    - Futures trading fees (typically 0.02-0.04% for maker/taker)
    - Funding rates for perpetual futures positions
  - (Future) Simulates market impact and slippage.
- **Data Handling**: The engine must be capable of processing OHLCV (Open, High, Low, Close, Volume) data for various timeframes (e.g., 1m, 5m, 1h, 1d).

### 3.2. Strategy Development Framework

- **Python-Based Structure**: Users will implement strategies by inheriting from a base Strategy class in Python.
- **Standardized Methods**: The base class will define key methods for the user to override:
  - `initialize()`: Called once at the start of a backtest. Used for setting up indicators, parameters, and initial state.
  - `on_data(data)`: Called for each new data point (bar). This is where the core trading logic will reside.
- **Simple API for Trading**: The framework will provide simple commands for the strategy to execute, such as:
  - `self.buy(amount, leverage=1)` - Open long position
  - `self.sell(amount, leverage=1)` - Open short position
  - `self.close_position(percentage=100)` - Close position (partial or full)
  - `self.get_position_size()` - Get current position size (positive for long, negative for short)
  - `self.get_cash()` - Get available cash/margin
  - `self.get_margin_ratio()` - Get current margin ratio
  - `self.get_unrealized_pnl()` - Get unrealized profit/loss
  - `self.get_leverage()` - Get current leverage ratio
- **Indicator Library Integration**: The framework should allow for easy integration with popular Python technical analysis libraries like TA-Lib or pandas-ta.

### 3.3. API (FastAPI)

A RESTful API will serve as the backend for the application.

- **POST /backtest**:
  - **Request**: Accepts Python code for a strategy, a selected symbol (e.g., BTCUSDT), a timeframe, date range, trading mode (spot/futures), and optional leverage settings.
  - **Action**: Initiates a new backtest run.
  - **Response**: Returns a unique backtest_id and a status of "running".
- **GET /backtest/{backtest_id}**:
  - **Action**: Retrieves the status and results of a specific backtest. If complete, it returns the performance metrics and chart data.
- **GET /data/symbols**:
  - **Action**: Returns a list of available trading pairs from the Binance dataset.
- **GET /data/history**:
  - **Action**: Returns historical OHLCV data for a given symbol and timeframe.

### 3.4. Results, Metrics, & Visualization

- **Web-Based Frontend**: A simple, clean web interface will be the primary way users interact with the platform.
- **Interactive Chart**:
  - Display OHLCV data using a candlestick or line chart (e.g., using Plotly, ECharts, or TradingView's Lightweight Charts).
  - Overlay buy (▲) and sell (▼) markers on the chart at the points where trades were executed.
  - Allow panning and zooming through the time series.
- **Key Performance Indicators (KPIs)**: The following metrics must be calculated and displayed for each backtest result:
  - **Overall Performance**:
    - Total PnL (Profit and Loss)
    - Total Return (%)
    - Ending Portfolio Value
    - Realized vs Unrealized PnL
  - **Risk-Adjusted Return**:
    - Sharpe Ratio
    - Sortino Ratio (Future)
  - **Risk Metrics**:
    - Max Drawdown (%)
    - Volatility
    - **Liquidation Statistics**:
      - Number of liquidations
      - Total liquidation losses
      - Largest liquidation loss
  - **Trade Statistics**:
    - Total Number of Trades (Long vs Short breakdown)
    - Win Rate (%) for Long and Short positions
    - Profit Factor (Gross Profit / Gross Loss)
    - Average Win / Average Loss
    - **Leverage Statistics**:
      - Average leverage used
      - Maximum leverage used
      - Time spent at different leverage levels

## 4. Technical Stack

- **Backend**: Python 3.9+
- **API Framework**: FastAPI
- **Data Analysis**: Pandas, NumPy
- **Technical Indicators**: pandas-ta or a similar library
- **Frontend**: HTML, CSS, JavaScript (No complex framework needed for V1, but could use Vue/React later)
- **Charting Library**: Plotly.js, ECharts, or Lightweight Charts
- **Data Source**: Historical OHLCV data files downloaded from Binance (e.g., in CSV or Parquet format)

## 5. Future Roadmap (Post V1)

- **Multi-Asset Backtesting**: Allow strategies to trade multiple symbols simultaneously.
- **Parameter Optimization**: Create tooling to run a backtest multiple times with a range of strategy parameters to find the optimal configuration.
- **Live Trading Integration**: Connect the strategy framework to the Binance API for real-time, paper, or live trading.
- **Database Integration**: Store backtest results, strategies, and metadata in a database (e.g., PostgreSQL, SQLite) for better organization and analysis.
- **Advanced Slippage & Latency Models**: Implement more realistic models for market friction.
- **Machine Learning Integration**: Allow for the integration of ML models (e.g., from Scikit-learn, TensorFlow) into the strategy logic.

## 6. Key Decisions & Assumptions

- **Strategy Submission**: For the initial version, users will submit their Python strategy code via a simple file upload. An embedded code editor may be considered for a future release.
- **Data Management**: The application will manage its own data. The historical market data will be provided locally within a data/ directory, managed by the application itself, not the user.
- **Data Granularity**: The system will ingest raw trade data. It will be responsible for processing and resampling this data into various standard OHLCV timeframes (e.g., 1m, 5m, 1h, 4h, 1d) as required by the user's strategy. This provides maximum flexibility.
- **Trading Mode**: The platform will support both spot and futures trading modes:
  - **Spot Trading**: Traditional buy/sell with no leverage, using actual asset ownership
  - **Futures Trading**: Leveraged trading with margin requirements, funding rates, and liquidation risks
- **Margin Calculations**: Use industry-standard margin calculations similar to major exchanges:
  - Initial margin = Position size / Leverage
  - Maintenance margin = Position size × Maintenance margin rate (typically 0.5-1%)
  - Liquidation occurs when unrealized losses exceed available margin buffer
