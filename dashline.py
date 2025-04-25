# dashboard.py
import threading, time
import streamlit as st
from engine import run_live

state = {"price":0, "fast_ma":0, "slow_ma":0, "position":0, "pnl":0}

threading.Thread(
    target=lambda: run_live("BTC/USDT", lambda s: state.update(s)),
    daemon=True
).start()

st.title("Live MA Crossover Dashboard")
price_box = st.empty()
fast_box  = st.empty()
slow_box  = st.empty()
pos_box   = st.empty()
pnl_box   = st.empty()

while True:
    price_box.metric("Price", f"{state['price']:.2f}")
    fast_box.metric("Fast MA", f"{state['fast_ma']:.2f}")
    slow_box.metric("Slow MA", f"{state['slow_ma']:.2f}")
    pos_box.metric("Position", "Long" if state["position"] else "Flat")
    pnl_box.metric("P&L", f"{state['pnl']:.2f}")
    time.sleep(1)
