# Hyperliquid Funding Arbitrage & Market-Making Framework
A quantitative trading framework featuring a delta-neutral funding rate backtesting engine and a live market-making execution client built for the Hyperliquid L1 order book.
## Strategy Architecture
1. **Backtester (`backtester/backtest_engine.py`)**:
   - Implements state-machine logic to harvest perp funding yields while maintaining a delta-neutral stance.
   - Amortizes fixed maker/taker execution fees across dynamic multi-hour hold horizons.
   - Computes annualized Sharpe Ratio, Max Drawdown, and includes parameter optimization.
2. **Live Execution Client (`live_bot/main.py`)**:
   - Integrates directly with the `hyperliquid-python-sdk`.
   - Routes **Add-Liquidity-Only (ALO)** limit orders to guarantee Maker fee tier status (0.015%).
   - Features built-in `DRY_RUN` mode for risk-free simulation.
## Project Structure
```text
hyperliquid-funding-arbitrage-bot/
├── backtester/
│   ├── cleaned_hourly_data-selected-columns.csv
│   └── backtest_engine.py
├── live_bot/
│   └── main.py
├── .gitignore
├── requirements.txt
└── README.md

## AUTHOR
David Kogi
