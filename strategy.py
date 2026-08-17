"""EMA Trend-Pullback + RSI Momentum Engine calculation and signal evaluation."""
import pandas as pd
import numpy as np
from typing import Optional, Literal

SignalType = Literal["BUY", "SELL", "HOLD"]

class StrategyEngine:
    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Computes EMA 200, 50, 20, RSI 7, and ATR 14."""
        df = df.copy()
        
        # Exponential Moving Averages
        df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
        df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
        df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()

        # Relative Strength Index (RSI 7)
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/7, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/7, adjust=False).mean()
        rs = gain / (loss + 1e-9)
        df["rsi"] = 100 - (100 / (1 + rs))

        # Average True Range (ATR 14)
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = tr.rolling(window=14).mean().fillna(tr)

        return df

    @staticmethod
    def evaluate_signal(df: pd.DataFrame) -> SignalType:
        """Evaluates entry criteria on the latest completed candle (index -2)."""
        if len(df) < 205:
            return "HOLD"

        curr = df.iloc[-2]  # Completed candle
        prev = df.iloc[-3]  # Preceding completed candle

        # BUY Rules
        bullish_trend = curr["close"] > curr["ema_200"] and curr["ema_20"] > curr["ema_50"]
        in_buy_zone = (curr["low"] <= curr["ema_20"]) and (curr["close"] >= curr["ema_50"])
        rsi_buy_trigger = (prev["rsi"] <= 35) and (curr["rsi"] > 40)
        bullish_candle = curr["close"] > curr["open"]

        if bullish_trend and in_buy_zone and rsi_buy_trigger and bullish_candle:
            return "BUY"

        # SELL Rules
        bearish_trend = curr["close"] < curr["ema_200"] and curr["ema_20"] < curr["ema_50"]
        in_sell_zone = (curr["high"] >= curr["ema_20"]) and (curr["close"] <= curr["ema_50"])
        rsi_sell_trigger = (prev["rsi"] >= 65) and (curr["rsi"] < 60)
        bearish_candle = curr["close"] < curr["open"]

        if bearish_trend and in_sell_zone and rsi_sell_trigger and bearish_candle:
            return "SELL"

        return "HOLD"