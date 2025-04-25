# Live MA Crossover Dashboard

Event-Driven MA Crossover Strategy with Live Data & Dashboard

A full-stack prototype demonstrating real-time data ingestion, asynchronous strategy execution, and live visualization for a moving-average crossover strategy. Designed to showcase your ability to move from backtest to live prototyping, this project:

- Fetches live price ticks via CCXT (crypto) or Alpaca (equities)
- Processes data in an `asyncio` event loop
- Executes MA crossover logic (with long-only or long/short modes)
- Presents an interactive dashboard in Dash or Streamlit
- Logs trade history and computes live performance metrics


## 🔧 Requirements
- **Python 3.8+**
- **pip** for installing packages

### Python Dependencies
ccxt                 # or alpaca-trade-api for equities
numpy                # numerical computing
pandas               # data manipulation & metrics
dash                 # for Plotly Dash dashboard
# OR
streamlit            # for simpler dashboards (recommd)
python-dotenv        # load environment variables


## Configuration
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and set:
   - `API_KEY` / `API_SECRET` (if using Alpaca or CCXT private endpoints)
   - `SYMBOL` (e.g. `BTC/USDT` or `AAPL`)
   - `FAST_MA` / `SLOW_MA` (optional override)

---


### 1. Run the Engine & Strategy
This starts the async loop fetching live ticks and updating strategy state:

```bash
python engine.py
```

You can also import and call in your own script:

```python
from engine import run_live
# record callback writes state to a list or DB
run_live(symbol="BTC/USDT", callback=record)
```

### 2. Launch the Dashboard
Depending on your preference:

- **Dash**
  ```bash
  python dashboard.py
  # Opens at http://127.0.0.1:8050
  ```
- **Streamlit**
  ```bash
  streamlit run dashboard.py
  # Opens at http://localhost:8501
  ```

The dashboard displays:
- Latest price, fast & slow MA values
- Current position (Flat / Long / Short)
- Realized P&L
- (Optional) Live charts & trade history table

---

## 📈 Strategy Details
- **Moving Averages**: Simple MA over `fast` & `slow` windows
- **Signals**:
  - **Long entry** when `fast_ma > slow_ma` and no position
  - **Long exit** when `fast_ma < slow_ma` and in long
  - **(Optional) Short entry/exit** if enabled
- **State Tracking**: Maintains
  - `position` (–1, 0, +1) (short, flat, and long respectively)
  - `entry_price`, `cumulative_pnl`
  - Price buffer for MA computation

All logic resides in `LiveMaStrategy.on_price()` in `engine.py`.

---

Example:
```python
import pandas as pd
history = pd.DataFrame(records)
history.set_index('timestamp', inplace=True)
# Compute Sharpe
rets = history['pnl'].diff().dropna()
sharpe = rets.mean()/rets.std()*np.sqrt(252)
```

---

## 📝 License
This project is licensed under the [MIT License](LICENSE).

---

*Happy coding & trading!*

