# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a crypto-trading project in its initial setup phase. The project uses Python 3.13+ and is configured with a minimal pyproject.toml file.

## Project Structure

Currently, this is a fresh Python project with:
- `pyproject.toml` - Python project configuration (minimal setup, no dependencies yet)
- `.venv/` - Python virtual environment
- `.idea/` - PyCharm/IntelliJ IDE configuration

## Development Setup

This project uses `uv` for Python package management:

1. **Sync dependencies**: `uv sync`
2. **Install project in development mode**: `uv pip install -e .`

## Common Commands

As the project develops, common commands will likely include:
- Add dependencies: `uv add <package>`
- Add dev dependencies: `uv add --dev <package>`
- Run in virtual environment: `uv run <command>`
- Run tests: `uv run pytest` (when tests are added)
- Format and lint code: `uv run ruff check --fix` (when ruff is added)

## Architecture Notes

This project appears to be focused on cryptocurrency trading. As the codebase grows, consider organizing around:
- Trading strategies
- Market data handling
- Portfolio management  
- Risk management
- Backtesting framework

The project currently has no source code, so the specific architecture will emerge as development progresses.