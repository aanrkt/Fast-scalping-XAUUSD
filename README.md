# ⚡ XAUUSD M5 Fast Scalping Bot (MetaTrader 5)

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-MetaTrader%205-green.svg)](https://www.metatrader5.com/)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest%20passing-brightgreen.svg)](test_bot.py)

A production-grade, modular, and resilient algorithmic trading system tailored for **XAUUSD (Gold)** on the **M5 (5-Minute)** timeframe. Powered by an **EMA Trend-Pullback + RSI Momentum Engine**, dynamic **ATR-based risk management**, automatic **Partial Take-Profit & Break-Even (BE)** shifting, and high-impact **Economic News Protection**.

---

## 📑 Table of Contents
- [Key Features](#-key-features)
- [Trading Strategy Logic](#-trading-strategy-logic)
- [Architecture & File Structure](#-architecture--file-structure)
- [Prerequisites & Installation](#-prerequisites--installation)
- [Configuration (.env)](#-configuration-env)
- [Running the Bot](#-running-the-bot)
- [Unit Testing & Dry-Run Mode](#-unit-testing--dry-run-mode)
- [Database & Logging Schema](#-database--logging-schema)
- [Live Trading Safety Checklist](#-live-trading-safety-checklist)
- [Disclaimer](#-disclaimer)

---

## 🚀 Key Features

* **Strict Trend & Momentum Engine**: Combines Macro EMA 200, Dynamic EMA 20/50 pullback channel, RSI (7) oversold/overbought momentum crosses, and ATR (14) volatility.
* **Smart Risk & Trade Management**:
  * Fixed fractional risk per trade (default 1.0% equity).
  * Dynamic Stop Loss calculated from local market volatility ($1.0 \times \text{ATR}$).
  * **Partial Take-Profit (TP1)** at $1.2R$ (closes 50% volume).
  * **Automatic Break-Even (BE)** shift to entry price + spread buffer immediately upon reaching TP1.
  * **Runner Target (TP2)** at $2.0R$ on the remaining 50% position.
* **High-Impact News Protection**: Blocks new entries 30 mins before/after Red-Folder USD events and closes vulnerable open positions 15 mins prior to imminent data releases.
* **Production Resilience**:
  * Bounded retry logic for API order submissions.
  * Duplicate-order protection & state tracking.
  * Graceful shutdown handlers (`SIGINT`, `SIGTERM`).
  * In-memory + SQLite persistent state recovery.
* **Structured Logging & Trade Journal**: Rotating JSON log files and SQLite database tracking every order ticket, execution slippage, fees, and realized PnL.

---

## 📈 Trading Strategy Logic

### 1. Indicators Setup (M5)
* **Macro Trend Filter**: 200-period Exponential Moving Average (`EMA 200`).
* **Dynamic Pullback Zone**: 20-period EMA (`EMA 20`) & 50-period EMA (`EMA 50`).
* **Momentum Filter**: 7-period Relative Strength Index (`RSI 7`).
* **Volatility Metric**: 14-period Average True Range (`ATR 14`).

### 2. Entry Rules

```
┌─────────────────────────────────────────────────────────────┐
│ BUY ENTRY                                                   │
├─────────────────────────────────────────────────────────────┤
│ 1. Trend: Close > EMA 200 AND EMA 20 > EMA 50               │
│ 2. Pullback: Low <= EMA 20 AND Close >= EMA 50              │
│ 3. Momentum: Prior RSI(7) <= 35 AND Current RSI(7) > 40     │
│ 4. Confirmation: Bullish Candle Close (Close > Open)        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ SELL ENTRY                                                  │
├─────────────────────────────────────────────────────────────┤
│ 1. Trend: Close < EMA 200 AND EMA 20 < EMA 50               │
│ 2. Pullback: High >= EMA 20 AND Close <= EMA 50             │
│ 3. Momentum: Prior RSI(7) >= 65 AND Current RSI(7) < 60     │
│ 4. Confirmation: Bearish Candle Close (Close < Open)        │
└─────────────────────────────────────────────────────────────┘
```

### 3. Exit & Execution Map
* **Initial Stop Loss (SL)**: $\text{Entry} \pm (1.0 \times \text{ATR})$.
* **Target 1 (TP1 - 1.2R)**: Closes 50% volume $\rightarrow$ Move SL to Entry + $\$0.10$ buffer.
* **Target 2 (TP2 - 2.0R)**: Full exit for remaining 50% runner.

---

## 🏗️ Architecture & File Structure

```text
xauusd_scalper/
├── .env.example          # Environment variables template
├── requirements.txt      # Python dependencies
├── config.py             # Pydantic schema validation & app settings
├── journal.py            # SQLite trade ledger & JSON structured logging
├── news_filter.py        # High-impact news event window blocker
├── risk_manager.py       # Contract size, fractional lot sizing, & level calculations
├── strategy.py           # Technical indicators calculation & signal evaluator
├── mt5_adapter.py        # MetaTrader 5 API bridge & retry execution handler
├── main.py               # Main trading loop, event handling & graceful shutdown
└── test_bot.py           # Pytest unit tests for sizing, indicators, and levels
```

---

## 🔧 Prerequisites & Installation

### Requirements
* Windows 10/11 or Windows Server (MetaTrader 5 desktop terminal required).
* Python 3.11 or higher.
* An active MT5 Demo or Live account with an authorized broker.

### Step-by-Step Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/xauusd-m5-scalper.git
   cd xauusd-m5-scalper
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Configuration (.env)

Copy the example environment file and configure your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your broker settings:

```ini
# MT5 Credentials & Server
MT5_ACCOUNT=12345678
MT5_PASSWORD=your_secure_password
MT5_SERVER=YourBroker-Demo
MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe

# Safe Mode / Paper Trading Switch
# Set to False ONLY when deploying with real capital!
DRY_RUN=True

# Trading Parameters
SYMBOL=XAUUSD
TIMEFRAME=M5
RISK_PER_TRADE_PCT=0.01
MAX_CONCURRENT_POSITIONS=1
MAGIC_NUMBER=20260817
SLIPPAGE_POINTS=20
```

---

## 🖥️ Running the Bot

### 1. Dry Run / Paper Trading (Default)
When `DRY_RUN=True`, the bot connects to MT5, processes real-time ticks and candle data, calculates signals, and simulates order executions without placing actual trades.

```bash
python main.py
```

### 2. Live / Real Money Execution
To enable live trading:
1. Ensure the **"Algo Trading"** button in MT5's top toolbar is **ON (Green)**.
2. In MT5: `Tools` $\rightarrow$ `Options` $\rightarrow$ `Expert Advisors` $\rightarrow$ Check **"Allow algorithmic trading"**.
3. Set `DRY_RUN=False` in your `.env` file.
4. Execute `python main.py`.

---

## 🧪 Unit Testing & Dry-Run Mode

Run the complete test suite using `pytest`:

```bash
pytest test_bot.py -v
```

Expected output:
```text
============================= test session starts =============================
test_bot.py::test_risk_manager_lot_calculation PASSED                    [ 33%]
test_bot.py::test_trade_levels_buy PASSED                                [ 66%]
test_bot.py::test_strategy_engine_indicators PASSED                       [100%]
============================== 3 passed in 0.42s ==============================
```

---

## 📊 Database & Logging Schema

### SQLite Ledger (`trades.db`)
All trade executions and status changes are permanently recorded:

| Column | Type | Description |
| :--- | :--- | :--- |
| `ticket` | `INTEGER PRIMARY KEY` | MT5 Order Deal / Ticket ID |
| `symbol` | `TEXT` | Symbol (e.g. `XAUUSD`) |
| `order_type` | `TEXT` | `BUY` or `SELL` |
| `lot` | `REAL` | Total executed volume |
| `open_price` | `REAL` | Fill price |
| `sl` / `tp1` / `tp2` | `REAL` | Dynamic price targets |
| `partial_done` | `INTEGER` | `1` if 50% TP1 was hit and SL moved to BE |
| `pnl` | `REAL` | Realized profit / loss |
| `status` | `TEXT` | `OPEN`, `CLOSED`, or `CLOSED_NEWS` |

### JSON Structured Log (`trading_bot.log`)
```json
{"timestamp": "2026-08-17 14:30:00,123", "level": "INFO", "module": "mt5_adapter", "message": "Order #999999 executed successfully @ 2450.50"}
{"timestamp": "2026-08-17 14:35:10,450", "level": "INFO", "module": "main", "message": "Target 1.2R reached for #999999. Executing 50% partial profit."}
{"timestamp": "2026-08-17 14:35:11,002", "level": "INFO", "module": "main", "message": "SL moved to Break-Even (2450.60) for #999999"}
```

---

## 🛡️ Live Trading Safety Checklist

Before switching `DRY_RUN=False`:

- [ ] **Demo Validation**: Tested on Demo account for at least 2 weeks of live market conditions.
- [ ] **Spread & Commission**: Verified that broker raw spreads on XAUUSD are $\le 15$ points ($1.5$ pips).
- [ ] **Low-Latency VPS**: Hosted on a dedicated Windows VPS located close to the broker server ($< 5\text{ms}$ latency).
- [ ] **Rollover Avoidance**: Ensure bot is not actively opening positions during daily rollover (23:59 – 00:05 Server Time).
- [ ] **Backup Power / Connectivity**: VPS equipped with auto-restart and watchdog process.

---

## ⚠️ Disclaimer

Trading Forex, Gold (CFDs), and leveraged financial instruments involves substantial risk of loss and is not suitable for all investors. Past performance of any strategy or backtest does not guarantee future results. **Use this software at your own risk.** Always test thoroughly on a demo environment before committing real capital.
