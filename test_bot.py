"""Unit tests verifying position calculations, levels, and signal integrity."""
import pytest
import pandas as pd
import numpy as np
from risk_manager import RiskManager
from strategy import StrategyEngine

def test_risk_manager_lot_calculation():
    rm = RiskManager(risk_pct=0.01, contract_size=100.0, volume_min=0.01, volume_step=0.01)
    # Balance $10,000 | 1% risk = $100 | SL distance = $2.00/oz -> Risk/lot = $200 -> Lot = 0.50
    lot = rm.calculate_lot_size(balance=10000, entry_price=2400.0, sl_price=2398.0)
    assert lot == 0.50

def test_trade_levels_buy():
    rm = RiskManager(risk_pct=0.01)
    levels = rm.calculate_trade_levels("BUY", entry_price=2400.0, atr=2.0, atr_mult=1.0, tp1_r=1.2, tp2_r=2.0)
    assert levels["sl"] == 2398.00
    assert levels["tp1"] == 2402.40
    assert levels["tp2"] == 2404.00
    assert levels["be"] == 2400.10

def test_strategy_engine_indicators():
    dates = pd.date_range(start="2026-01-01", periods=250, freq="5min")
    dummy_data = pd.DataFrame({
        "time": dates,
        "open": np.linspace(2300, 2400, 250),
        "high": np.linspace(2302, 2402, 250),
        "low": np.linspace(2298, 2398, 250),
        "close": np.linspace(2301, 2401, 250),
        "tick_volume": 100
    })
    df = StrategyEngine.calculate_indicators(dummy_data)
    assert "ema_200" in df.columns
    assert "rsi" in df.columns
    assert "atr" in df.columns
    assert not df["rsi"].isna().all()
