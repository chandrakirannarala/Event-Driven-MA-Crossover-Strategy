import asyncio
import ccxt.async_support as ccxt  # for crypto; swap to alpaca_trade_api for equities
import numpy as np
from collections import deque
import threading
import time
import os

# Import metrics after defining the class to avoid circular imports
# The metrics module will be imported inside the run_live function

class LiveMaStrategy:
    def __init__(self, symbol, fast=10, slow=20, tracker=None):
        self.symbol = symbol
        self.fast, self.slow = fast, slow
        self.prices = deque(maxlen=slow)
        self.position = 0       # 0 = flat, 1 = long, -1 = short
        self.entry_price = 0.0
        self.pnl = 0.0
        # Add performance tracker
        self.tracker = tracker

    def on_price(self, price):
        """Call on each new price; returns state dict when ready."""
        # Measure memory usage periodically
        if self.tracker:
            self.tracker.get_memory_usage()
            
        self.prices.append(price)
        if len(self.prices) < self.slow:
            return None

        fast_ma = np.mean(list(self.prices)[-self.fast:])
        slow_ma = np.mean(self.prices)
        signal = False
        old_position = self.position
        transaction_data = {
            'price': price,
            'is_entry': False,
            'position': self.position,
            'pnl': self.pnl
        }
        
        if fast_ma > slow_ma and self.position == 0:
            self.position = 1
            self.entry_price = price
            signal = True
            transaction_data['is_entry'] = True
            transaction_data['position'] = self.position
            
        elif fast_ma < slow_ma and self.position == 1:
            self.pnl += price - self.entry_price
            self.position = 0
            signal = True
            transaction_data['pnl'] = self.pnl
            transaction_data['position'] = self.position
        
        elif fast_ma < slow_ma and self.position == 0:
            self.position = -1       # enter short
            self.entry_price = price
            signal = True
            transaction_data['is_entry'] = True
            transaction_data['position'] = self.position
            
        elif fast_ma > slow_ma and self.position == -1:
            self.pnl += self.entry_price - price
            self.position = 0        # close short
            signal = True
            transaction_data['pnl'] = self.pnl
            transaction_data['position'] = self.position

        # Log transaction if position changed and we have a tracker
        if signal and self.tracker:
            self.tracker.log_transaction(transaction_data)

        return {
            "price": price,
            "fast_ma": fast_ma,
            "slow_ma": slow_ma,
            "position": self.position,
            "pnl": self.pnl,
        }

async def feed_loop(strategy, callback, delay=1, max_retries=5, tracker=None):
    exchange = ccxt.kraken({'enableRateLimit': True})
    await exchange.load_markets()
    retry = 0
    while True:
        try:
            # Measure latency if we have a tracker
            if tracker:
                # Use the tracker to measure latency for the fetch_ticker operation
                ticker, latency = await tracker.measure_latency(
                    exchange.fetch_ticker, strategy.symbol
                )
            else:
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

# Main function to run the strategy with metrics
def run_live(symbol, callback, enable_metrics=False):
    # Use a function to wrap the async code
    def run_async_loop():
        # Now import metrics to avoid circular imports
        from metrics import PerformanceTracker, get_event_loop_in_thread
        
        # Initialize performance tracker if metrics are enabled
        tracker = PerformanceTracker() if enable_metrics else None
        
        strat = LiveMaStrategy(symbol, tracker=tracker)
        
        # Get or create event loop for this thread
        loop = get_event_loop_in_thread()
        
        # Create task for the feed loop
        feed_task = loop.create_task(feed_loop(strat, callback, tracker=tracker))
        
        # If metrics are enabled, add a task to print reports periodically
        if tracker:
            async def print_metrics_report():
                while True:
                    await asyncio.sleep(3600)  # Print report every hour
                    print(tracker.get_report())
                    
            metrics_task = loop.create_task(print_metrics_report())
            tasks = [feed_task, metrics_task]
        else:
            tasks = [feed_task]
        
        try:
            loop.run_until_complete(asyncio.gather(*tasks))
        except KeyboardInterrupt:
            print("Shutting down...")
            # Print final report if we have a tracker
            if tracker:
                print(tracker.get_report())
                
            for task in tasks:
                task.cancel()
            
            # Clean up pending tasks
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            loop.close()
    
    # Start in the current thread if this is the main program
    if threading.current_thread() is threading.main_thread():
        run_async_loop()
    else:
        # Create a new thread for asyncio
        asyncio_thread = threading.Thread(target=run_async_loop)
        asyncio_thread.daemon = True
        asyncio_thread.start()
        return asyncio_thread

# Example of running with metrics enabled
if __name__ == "__main__":
    def simple_callback(state):
        print(f"Price: {state['price']:.2f}, Position: {state['position']}, PnL: {state['pnl']:.2f}")
        
    run_live("BTC/USDT", simple_callback, enable_metrics=True)