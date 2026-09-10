import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


class FundingArbitrageBacktest:
    """Quantitative backtesting engine for single-venue cash-and-carry funding arbitrage on Hyperliquid."""

    def __init__(
        self,
        filepath: str = "cleaned_hourly_data-selected-columns.csv",
        coin: str = "BTC",
        entry_threshold: float = 0.000020,  # ~17.5% APR yield trigger
        exit_threshold: float = 0.000005,  # ~4.3% APR exit trigger
        maker_fee: float = 0.000050,  # 0.005% maker fee per execution leg
    ):
        self.filepath = filepath
        self.coin = coin
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.maker_fee = maker_fee
        self.data = None
        self.results = None

    def load_and_preprocess(self):
        """Loads historical CSV data, filters by target coin, and formats timestamps."""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(
                f"Data file '{self.filepath}' not found. Please ensure it is in the same directory."
            )

        df = pd.read_csv(self.filepath)

        # Filter coin and sort chronologically
        df = (
            df[df["coin"] == self.coin]
            .sort_values("hour_ts")
            .reset_index(drop=True)
        )

        # Convert Unix timestamp to readable datetime
        df["datetime"] = pd.to_datetime(df["hour_ts"], unit="s")

        # Forward fill missing funding rates to maintain continuous series
        cols = ["datetime", "mid", "funding", "premium"]
        df = df[cols].copy()
        df[["funding", "premium"]] = df[["funding", "premium"]].ffill()
        df = df.dropna().reset_index(drop=True)

        self.data = df
        return self

    def generate_signals_and_simulate(self):
        """Executes state-machine logic to simulate market entry, exit, and transaction drag."""
        df = self.data.copy()

        position = 0
        positions = []
        funding_pnl = []
        trading_fees = []

        for i in range(len(df)):
            funding_rate = df.loc[i, "funding"]
            fees = 0.0

            # Causal State-Machine Logic
            if position == 0:
                # Open position ONLY if funding yield exceeds entry threshold
                if funding_rate > self.entry_threshold:
                    position = -1  # Short perp, collect positive yield
                    fees = (
                        self.maker_fee * 2
                    )  # Entry execution fee (Spot + Perp)
                elif funding_rate < -self.entry_threshold:
                    position = 1  # Long perp, receive yield on negative funding
                    fees = self.maker_fee * 2
            elif position == 1:
                # Exit position when yield compresses below exit threshold
                if funding_rate >= -self.exit_threshold:
                    position = 0
                    fees = (
                        self.maker_fee * 2
                    )  # Exit execution fee (Spot + Perp)
            elif position == -1:
                # Exit position when yield compresses below exit threshold
                if funding_rate <= self.exit_threshold:
                    position = 0
                    fees = self.maker_fee * 2

            # Continuous hourly cashflow generated while holding position
            hourly_cashflow = -position * funding_rate

            positions.append(position)
            funding_pnl.append(hourly_cashflow)
            trading_fees.append(fees)

        df["position"] = positions
        df["funding_pnl"] = funding_pnl
        df["trading_fees"] = trading_fees

        # Strategy net returns after deducting execution friction
        df["net_return"] = df["funding_pnl"] - df["trading_fees"]
        df["cumulative_return"] = (1 + df["net_return"]).cumprod() - 1

        self.results = df
        return self

    def calculate_performance_metrics(self) -> dict:
        """Calculates key quantitative metrics including total return, Sharpe Ratio, and Max Drawdown."""
        if self.results is None:
            raise ValueError(
                "Run simulation before calculating metrics."
            )

        df = self.results
        net_returns = df["net_return"]

        total_return = df["cumulative_return"].iloc[-1]

        # Calculate Annualized Sharpe Ratio (8,760 hours per year)
        mean_return = net_returns.mean()
        std_return = net_returns.std()
        sharpe_ratio = (
            (mean_return / std_return) * np.sqrt(8760)
            if std_return > 0
            else 0.0
        )

        # Calculate Maximum Drawdown
        cum_returns = (1 + net_returns).cumprod()
        peak = cum_returns.cummax()
        drawdown = (cum_returns - peak) / peak
        max_drawdown = drawdown.min()

        return {
            "Total Return (%)": total_return * 100,
            "Sharpe Ratio": sharpe_ratio,
            "Max Drawdown (%)": max_drawdown * 100,
            "Total Trades Executed": (df["trading_fees"] > 0).sum(),
        }


def run_grid_search_optimization(
    filepath: str, coin: str = "BTC"
) -> pd.DataFrame:
    """Grid search optimization to find optimal entry/exit threshold parameters."""
    entry_range = np.linspace(0.000010, 0.000050, 5)
    exit_range = np.linspace(0.000001, 0.000010, 5)

    results_matrix = np.zeros((len(entry_range), len(exit_range)))

    for i, entry in enumerate(entry_range):
        for j, exit_val in enumerate(exit_range):
            if exit_val >= entry:
                results_matrix[i, j] = np.nan
                continue

            bt = FundingArbitrageBacktest(
                filepath=filepath,
                coin=coin,
                entry_threshold=entry,
                exit_threshold=exit_val,
            )
            bt.load_and_preprocess().generate_signals_and_simulate()
            metrics = bt.calculate_performance_metrics()
            results_matrix[i, j] = metrics["Sharpe Ratio"]

    df_grid = pd.DataFrame(
        results_matrix,
        index=[f"{x:.6f}" for x in entry_range],
        columns=[f"{y:.6f}" for y in exit_range],
    )
    return df_grid


# --- MAIN BACKTEST EXECUTION ---
if __name__ == "__main__":
    DATA_FILE = "cleaned_hourly_data-selected-columns.csv"

    print("=== RUNNING SINGLE BACKTEST SIMULATION ===")
    backtest = FundingArbitrageBacktest(
        filepath=DATA_FILE,
        coin="BTC",
        entry_threshold=0.000020,
        exit_threshold=0.000005,
        maker_fee=0.000050,
    )

    try:
        backtest.load_and_preprocess().generate_signals_and_simulate()
        metrics = backtest.calculate_performance_metrics()

        print("\n=== PERFORMANCE RESULTS ===")
        for key, val in metrics.items():
            print(f"{key:<22}: {val:.4f}")

    except FileNotFoundError as e:
        print(f"\n[Warning] {e}")
        print(
            "Please ensure 'cleaned_hourly_data-selected-columns.csv' is in your directory to run."
        )
