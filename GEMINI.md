# zettaranc-skill Project Instructions

This project is a Python-based quantitative trading toolset plus an AI role
protocol, based on the investment framework of zettaranc (万千). It integrates
real market data, technical indicator calculation, and strategy detection. The
character-based commentary is produced by the host LLM (Claude Code / Cursor),
which reads `SKILL.md` and `knowledge/` directly — the project itself ships no
bundled LLM or RAG service.

## Project Overview

- **Purpose:** To provide a comprehensive system for stock analysis, strategy
  backtesting, and persona-driven decision support using a specific investment
  philosophy.
- **Core Technologies:**
  - **Language:** Python 3.10+
  - **Data Source:** Tushare API (requires `TUSHARE_TOKEN` + `TUSHARE_API_URL`).
  - **Database:** SQLite (stored in `data/stock_data.db` by default).
  - **Analysis:** Pandas (vectorized indicator calculations), Technical indicators (60+), Strategies (30+).
  - **Interaction:** CLI (via `modules/cli.py`, exposes `--json` for hosts).
- **Architecture:**
  - **Data Layer:** Tushare API -> `data_sync.py` -> SQLite.
  - **Logic Layer:** `indicators/` (calculation) -> `strategies/` (detection) -> `screener.py` / `backtest.py`.
  - **Interface Layer:** `cli.py` (tools, `--json` output) consumed by the host; `SKILL.md` (persona) loaded by the host LLM.

## Building and Running

### Setup
1. **Environment (uv preferred):**
   ```bash
   uv sync --extra dev
   cp .env.example .env  # Configure TUSHARE_TOKEN, TUSHARE_API_URL and DATA_MODE
   ```
2. **Initialization:**
   ```bash
   uv run python -m modules.database  # Create tables
   uv run python -m modules.data_sync sync  # Sync basic stock info (once)
   ```

### Key Commands
- **Sync Data:** `uv run python -m modules.data_sync sync --ts_code <CODE> --days <DAYS>`
- **Analyze Stock:** `uv run zt analyze <CODE>` (or `uv run python -m modules.cli analyze <CODE>`)
- **Screen Stocks:** `uv run zt screen --strategy <STRATEGY> --limit 20`
- **Watchlist:** `uv run zt watchlist scan`
- **Run Tests:** `uv run python -m pytest tests/`

## Development Conventions

### Coding Style
- **Pythonic:** Follow PEP 8. Use type hints for function signatures.
- **Data Preparation:** The Python layer is responsible for all data retrieval and calculation. Persona commentary and role-playing are left to the host LLM, not the Python layer.
- **Modularity:** Keep indicators in `modules/indicators/` and strategies in `modules/strategies/`.
- **Performance:** Prefer Pandas vectorized operations over loops for technical indicator calculations.

### Testing
- **Framework:** Pytest.
- **Execution:** Run `uv run python -m pytest tests/` before committing.
- **Isolation:** Ensure new strategies or indicators have corresponding unit tests in the `tests/` directory.

### Configuration
- Use `.env` for all sensitive information (Tokens).
- `DATA_MODE` options: `jnb` (Tushare + local data) or `websearch` (no external data; host answers from `SKILL.md` / `knowledge/` only).

## Key Files & Directories
- `SKILL.md`: The core persona definition and agentic protocol, loaded by the host LLM.
- `modules/`: Main source code (data + analysis layer).
- `knowledge/`: Trading system theory and documentation.
- `rules/`: Persona role frameworks for career and life advice (loaded by the host LLM).
- `data/`: Local SQLite database storage.
- `scripts/`: Batch processing and maintenance scripts.
