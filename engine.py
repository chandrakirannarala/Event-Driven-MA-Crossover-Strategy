import asyncio
import ccxt.async_support as ccxt        # for crypto; swap to alpaca_trade_api for equities
import numpy as np
from collections import deque

class LiveMaStrategy:
    def __init__(self, symbol, fast=10, slow=20):
        self.symbol = symbol
        self.fast, self.slow = fast, slow
        self.prices = deque(maxlen=slow)
        self.position = 0       # 0 = flat, 1 = long, -1 = short
        self.entry_price = 0.0
        self.pnl = 0.0

    def on_price(self, price):
        """Call on each new price; returns state dict when ready."""
        self.prices.append(price)
        if len(self.prices) < self.slow:
            return None

        fast_ma = np.mean(list(self.prices)[-self.fast:])
        slow_ma = np.mean(self.prices)
        signal = 0
        if fast_ma > slow_ma and self.position == 0:
            self.position = 1
            self.entry_price = price
        elif fast_ma < slow_ma and self.position == 1:
            self.pnl += price - self.entry_price
            self.position = 0
        
        elif fast_ma < slow_ma and self.position == 0:
            self.position = -1       # enter short
            self.entry_price = price

        elif fast_ma > slow_ma and self.position == -1:
            self.pnl += self.entry_price - price
            self.position = 0        # close short




        return {
            "price": price,
            "fast_ma": fast_ma,
            "slow_ma": slow_ma,
            "position": self.position,
            "pnl": self.pnl,
        }

async def feed_loop(strategy, callback, delay=1, max_retries=5):
    exchange = ccxt.kraken({'enableRateLimit': True})
    await exchange.load_markets()
    retry = 0
    while True:
        try:
            ticker = await exchange.fetch_ticker(strategy.symbol)
            retry = 0
            state = strategy.on_price(ticker['last'])
            if state:
                callback(state)
        except Exception as e:
            print(f"[Error] {e}, retrying in {delay * (2**retry):.1f}s")
            await asyncio.sleep(delay * (2**min(retry, max_retries)))
            retry += 1
        else:
            await asyncio.sleep(delay)


def run_live(symbol, callback):
    strat = LiveMaStrategy(symbol)
    asyncio.run(feed_loop(strat, callback))
