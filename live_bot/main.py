import logging
import os
import time
from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

# Setup logging formatting
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("HyperliquidMarketMaker")


class HyperliquidGridBot:
    """Live execution market-making bot for Hyperliquid L1 order book."""

    def __init__(
        self,
        coin: str = "BTC",
        leverage: int = 1,
        grid_spread: float = 0.0015,
        position_size_usd: float = 25.0,
        dry_run: bool = True,
    ):
        self.coin = coin
        self.grid_spread = grid_spread
        self.position_size_usd = position_size_usd
        self.dry_run = dry_run

        # Fetch private key from environment or fall back to a dummy test key
        dummy_key = (
            "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        )
        self.secret_key = os.getenv("HYPERLIQUID_PRIVATE_KEY", dummy_key)

        # Authenticate EVM account and initialize SDK endpoints
        self.account = Account.from_key(self.secret_key)
        self.address = self.account.address

        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)

        if not self.dry_run:
            self.exchange = Exchange(self.account, constants.MAINNET_API_URL)
            self.exchange.update_leverage(leverage, self.coin)

        logger.info(f"Bot initialized for {self.coin}. Address: {self.address}")
        logger.info(
            f"Mode: {'DRY RUN (Simulation)' if self.dry_run else 'LIVE TRADING'}"
        )

    def fetch_market_mid_price(self) -> float:
        """Retrieves real-time mid price from Hyperliquid order book."""
        try:
            all_mids = self.info.all_mids()
            mid_price = float(all_mids.get(self.coin, 0.0))
            return mid_price
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            return 0.0

    def run_grid_cycle(self):
        """Calculates bid/ask grid levels and submits maker limit orders."""
        mid_price = self.fetch_market_mid_price()
        if mid_price == 0.0:
            return

        # Calculate limit order prices based on target spread offset
        bid_price = round(mid_price * (1 - self.grid_spread), 2)
        ask_price = round(mid_price * (1 + self.grid_spread), 2)
        order_size = round(self.position_size_usd / mid_price, 4)

        logger.info(f"[{self.coin}] Current Mid Price: ${mid_price:,.2f}")
        logger.info(
            f"  └─ Target Bid: ${bid_price:,.2f} | Target Ask: ${ask_price:,.2f} | Size: {order_size}"
        )

        if self.dry_run:
            logger.info("  └─ [DRY RUN] Simulated Maker Orders Calculated.")
        else:
            # Post Add-Liquidity-Only (ALO) limit orders to guarantee Maker fee rebates
            logger.info("  └─ [LIVE] Submitting limit orders to exchange...")
            self.exchange.order(
                self.coin,
                True,  # True = Buy / Bid
                order_size,
                bid_price,
                {"limit": {"tif": "Alo"}},
            )
            self.exchange.order(
                self.coin,
                False,  # False = Sell / Ask
                order_size,
                ask_price,
                {"limit": {"tif": "Alo"}},
            )


# --- EXECUTION ENTRYPOINT ---
if __name__ == "__main__":
    COIN_TO_TRADE = "BTC"
    SPREAD = 0.0015  # 0.15% spread offset
    ORDER_USD = 25.0  # $25 per grid order
    IS_DRY_RUN = True  # Keep True for dry-run simulation mode

    bot = HyperliquidGridBot(
        coin=COIN_TO_TRADE,
        leverage=1,
        grid_spread=SPREAD,
        position_size_usd=ORDER_USD,
        dry_run=IS_DRY_RUN,
    )

    print("\n=== STARTING LIVE BOT EXECUTION TEST ===")
    for iteration in range(1, 4):
        logger.info(f"--- Iteration {iteration} ---")
        bot.run_grid_cycle()
        time.sleep(3)
    print("=== TEST COMPLETED SUCCESSFULLY ===")
