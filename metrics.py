import time
import psutil
import os
import pandas as pd
import numpy as np
from datetime import datetime
import threading
import json
import asyncio

class PerformanceTracker:
    def __init__(self, log_dir="./logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Performance metrics storage
        self.latencies = []
        self.transaction_times = []
        self.memory_samples = []
        self.trades = []
        
        # Initialize log files
        self.uptime_log = os.path.join(log_dir, "uptime_log.txt")
        self.metrics_log = os.path.join(log_dir, "metrics_log.json")
        self.trades_log = os.path.join(log_dir, "trade_history.csv")
        
        # Start uptime monitoring
        self._start_uptime_monitor()
        
        # Initial memory measurement
        self.initial_memory = self.get_memory_usage()
        
    def _start_uptime_monitor(self, interval=60):
        """Start a thread that logs uptime every interval seconds"""
        threading.Thread(
            target=self._uptime_logger,
            args=(interval,),
            daemon=True
        ).start()
        
    def _uptime_logger(self, interval):
        """Continuously log uptime at specified interval"""
        while True:
            self.log_uptime()
            time.sleep(interval)
    
    def log_uptime(self):
        """Log current timestamp as an uptime marker"""
        with open(self.uptime_log, "a") as f:
            f.write(f"{time.time()},UP\n")
    
    async def measure_latency(self, fetch_function, *args, **kwargs):
        """Measure and record latency for any async function call"""
        start_time = time.time()
        try:
            result = await fetch_function(*args, **kwargs)
            success = True
        except Exception as e:
            success = False
            result = None
        
        end_time = time.time()
        latency = end_time - start_time
        
        self.latencies.append({
            'timestamp': end_time,
            'latency': latency,
            'success': success
        })
        
        # Periodically save latencies
        if len(self.latencies) % 100 == 0:
            self._save_metrics()
            
        return result, latency
    
    def get_memory_usage(self):
        """Get current memory usage of the process"""
        process = psutil.Process(os.getpid())
        memory = process.memory_info().rss  # in bytes
        
        self.memory_samples.append({
            'timestamp': time.time(),
            'memory': memory
        })
        
        return memory
    
    def log_transaction(self, transaction_data):
        """Log a transaction with timestamp"""
        timestamp = time.time()
        self.transaction_times.append(timestamp)
        
        # Add transaction to trades log
        transaction = {
            'timestamp': timestamp,
            'price': transaction_data.get('price', 0),
            'position': transaction_data.get('position', 0),
            'pnl': transaction_data.get('pnl', 0),
            'type': 'ENTRY' if transaction_data.get('is_entry', False) else 'EXIT'
        }
        
        self.trades.append(transaction)
        
        # Save to CSV
        with open(self.trades_log, 'a') as f:
            if os.path.getsize(self.trades_log) == 0:
                # Write header if file is empty
                f.write("timestamp,price,position,pnl,type\n")
            f.write(f"{timestamp},{transaction['price']},{transaction['position']},{transaction['pnl']},{transaction['type']}\n")
    
    def calculate_metrics(self):
        """Calculate performance metrics"""
        metrics = {}
        
        # Calculate latency metrics
        if self.latencies:
            latency_values = [l['latency'] for l in self.latencies]
            metrics['avg_latency_ms'] = sum(latency_values) / len(latency_values) * 1000
            metrics['max_latency_ms'] = max(latency_values) * 1000
            metrics['min_latency_ms'] = min(latency_values) * 1000
            
            # Success rate
            success_count = sum(1 for l in self.latencies if l['success'])
            metrics['success_rate'] = success_count / len(self.latencies) * 100
        
        # Calculate uptime
        metrics['uptime_percentage'] = self._calculate_uptime()
        
        # Calculate memory optimization
        if self.memory_samples:
            current_memory = self.memory_samples[-1]['memory']
            metrics['memory_usage_bytes'] = current_memory
            metrics['memory_change_percentage'] = (current_memory - self.initial_memory) / self.initial_memory * 100
        
        # Calculate transaction metrics
        if self.transaction_times:
            # Total transactions
            metrics['total_transactions'] = len(self.transaction_times)
            
            # Peak transactions per minute
            start_time = min(self.transaction_times)
            end_time = max(self.transaction_times)
            metrics['peak_transactions_per_minute'] = self._calculate_peak_transactions(start_time, end_time)
        
        # Calculate Sharpe ratio if we have trade data
        if os.path.exists(self.trades_log) and os.path.getsize(self.trades_log) > 0:
            metrics['sharpe_ratio'] = self._calculate_sharpe_ratio()
        
        return metrics
    
    def _calculate_uptime(self):
        """Calculate uptime percentage based on log"""
        if not os.path.exists(self.uptime_log):
            return 0
            
        with open(self.uptime_log, 'r') as f:
            logs = f.readlines()
        
        if not logs:
            return 0
            
        # Parse timestamps
        timestamps = [float(line.split(',')[0]) for line in logs]
        
        if len(timestamps) < 2:
            return 0
            
        # Calculate expected number of entries
        first_timestamp = timestamps[0]
        last_timestamp = timestamps[-1]
        duration = last_timestamp - first_timestamp
        expected_entries = duration / 60  # Assuming 60-second intervals
        
        # Calculate uptime
        return min(100.0, (len(timestamps) / expected_entries) * 100)
    
    def _calculate_peak_transactions(self, start_time, end_time, window_size=60):
        """Calculate peak transactions per minute"""
        if not self.transaction_times:
            return 0
            
        max_count = 0
        for minute_start in range(int(start_time), int(end_time) + 1, window_size):
            minute_end = minute_start + window_size
            count = sum(1 for t in self.transaction_times if minute_start <= t < minute_end)
            max_count = max(max_count, count)
        
        return max_count
    
    def _calculate_sharpe_ratio(self):
        """Calculate Sharpe ratio from trade history"""
        try:
            trades_df = pd.read_csv(self.trades_log)
            if trades_df.empty:
                return 0
                
            # Convert timestamp to datetime
            trades_df['date'] = pd.to_datetime(trades_df['timestamp'], unit='s')
            
            # Calculate daily returns
            daily_returns = trades_df.groupby(pd.Grouper(key='date', freq='D'))['pnl'].sum()
            
            if len(daily_returns) < 2 or daily_returns.std() == 0:
                return 0
                
            # Calculate annualized Sharpe ratio
            sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
            return sharpe
        except Exception as e:
            print(f"Error calculating Sharpe ratio: {e}")
            return 0
    
    def _save_metrics(self):
        """Save current metrics to JSON file"""
        metrics = self.calculate_metrics()
        
        with open(self.metrics_log, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'metrics': metrics
            }, f, indent=2)
        
        return metrics
    
    def get_report(self):
        """Generate a comprehensive performance report"""
        metrics = self.calculate_metrics()
        
        report = f"""
PERFORMANCE METRICS REPORT
=========================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

LATENCY METRICS:
- Average Latency: {metrics.get('avg_latency_ms', 'N/A'):.2f} ms
- Maximum Latency: {metrics.get('max_latency_ms', 'N/A'):.2f} ms
- Success Rate: {metrics.get('success_rate', 'N/A'):.2f}%

UPTIME METRICS:
- Uptime: {metrics.get('uptime_percentage', 'N/A'):.2f}%

TRANSACTION METRICS:
- Total Transactions: {metrics.get('total_transactions', 'N/A')}
- Peak Transactions/Minute: {metrics.get('peak_transactions_per_minute', 'N/A')}

MEMORY METRICS:
- Current Memory Usage: {metrics.get('memory_usage_bytes', 'N/A')/1024/1024:.2f} MB
- Memory Change: {metrics.get('memory_change_percentage', 'N/A'):.2f}%

PERFORMANCE METRICS:
- Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A'):.2f}
"""
        return report

# Standalone function to get a new event loop for a thread
def get_event_loop_in_thread():
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        # If there's no event loop in this thread, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop