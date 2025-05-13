import threading
import time
import streamlit as st
import pandas as pd
import os
import json
from engine import run_live

# Global state for the dashboard
state = {
    "price": 0, 
    "fast_ma": 0, 
    "slow_ma": 0, 
    "position": 0, 
    "pnl": 0
}

# Function to update the global state
def update_state(new_state):
    state.update(new_state)

# Set up the Streamlit dashboard
st.set_page_config(
    page_title="Live MA Crossover Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("Live MA Crossover Dashboard")

# Create a two-column layout
col1, col2 = st.columns(2)

# Main metrics in the first column
with col1:
    st.subheader("Trading Metrics")
    price_box = st.empty()
    fast_box = st.empty()
    slow_box = st.empty()
    pos_box = st.empty()
    pnl_box = st.empty()

# Performance metrics in the second column
with col2:
    st.subheader("Performance Metrics")
    latency_box = st.empty()
    uptime_box = st.empty()
    transactions_box = st.empty()
    memory_box = st.empty()
    sharpe_box = st.empty()

# Function to load metrics from the log file
def load_metrics():
    metrics_log = os.path.join("./logs", "metrics_log.json")
    if os.path.exists(metrics_log):
        try:
            with open(metrics_log, 'r') as f:
                data = json.load(f)
                return data.get('metrics', {})
        except Exception as e:
            st.error(f"Error loading metrics: {e}")
    return {}

# Function to load trade history
def load_trade_history():
    trades_log = os.path.join("./logs", "trade_history.csv")
    if os.path.exists(trades_log) and os.path.getsize(trades_log) > 0:
        try:
            df = pd.read_csv(trades_log)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            return df
        except Exception as e:
            st.error(f"Error loading trade history: {e}")
    return pd.DataFrame()

# Add charts section
st.subheader("Trading History")
chart_container = st.container()

# Start the trading engine in a separate thread
symbol = "BTC/USDT"
engine_thread = run_live(symbol, update_state, enable_metrics=True)

# Main dashboard update loop
while True:
    # Update trading metrics
    price_box.metric("Price", f"{state['price']:.2f}")
    fast_box.metric("Fast MA", f"{state['fast_ma']:.2f}")
    slow_box.metric("Slow MA", f"{state['slow_ma']:.2f}")
    pos_box.metric("Position", "Long" if state["position"] == 1 else "Short" if state["position"] == -1 else "Flat")
    pnl_box.metric("P&L", f"{state['pnl']:.2f}")
    
    # Load performance metrics
    metrics = load_metrics()
    
    # Update performance metrics
    latency_box.metric("Avg. Latency", f"{metrics.get('avg_latency_ms', 0):.2f} ms")
    uptime_box.metric("Uptime", f"{metrics.get('uptime_percentage', 0):.2f}%")
    transactions_box.metric(
        "Transactions", 
        f"{metrics.get('total_transactions', 0)}",
        f"Peak: {metrics.get('peak_transactions_per_minute', 0)}/min"
    )
    memory_box.metric(
        "Memory Usage", 
        f"{metrics.get('memory_usage_bytes', 0)/1024/1024:.2f} MB", 
        f"{metrics.get('memory_change_percentage', 0):.2f}%"
    )
    sharpe_box.metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}")
    
    # Update charts if there's trade history
    with chart_container:
        df = load_trade_history()
        if not df.empty:
            st.line_chart(df.set_index('timestamp')['pnl'])
            
            # Show recent trades
            st.subheader("Recent Trades")
            st.dataframe(df.tail(10)[['timestamp', 'price', 'position', 'pnl', 'type']])
    
    # Sleep to avoid excessive updates
    time.sleep(1)