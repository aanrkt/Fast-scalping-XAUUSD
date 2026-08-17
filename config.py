"""Configuration loader and schema validator using Pydantic."""
import os
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    MT5_ACCOUNT: int = Field(..., description="MT5 Account Number")
    MT5_PASSWORD: str = Field(..., description="MT5 Password")
    MT5_SERVER: str = Field(..., description="MT5 Broker Server")
    MT5_PATH: str = Field(r"C:\Program Files\MetaTrader 5\terminal64.exe")

    # Safety Switch
    DRY_RUN: bool = Field(True, description="True for simulation/dry-run, False for actual execution")

    SYMBOL: str = Field("XAUUSD")
    TIMEFRAME: str = Field("M5")
    RISK_PER_TRADE_PCT: float = Field(0.01, ge=0.001, le=0.05, description="Risk between 0.1% and 5%")
    MAX_CONCURRENT_POSITIONS: int = Field(1, ge=1, le=3)
    MAGIC_NUMBER: int = Field(20260817)
    SLIPPAGE_POINTS: int = Field(20)

    # Strategy Parameters
    EMA_TREND: int = 200
    EMA_FAST: int = 20
    EMA_SLOW: int = 50
    RSI_PERIOD: int = 7
    ATR_PERIOD: int = 14
    ATR_MULTIPLIER: float = 1.0
    TP1_R_MULTIPLE: float = 1.2
    TP2_R_MULTIPLE: float = 2.0
    PARTIAL_CLOSE_RATIO: float = 0.5

    @field_validator("RISK_PER_TRADE_PCT")
    def validate_risk(cls, v: float) -> float:
        if v > 0.03:
            print(f"[WARNING] High risk level configured: {v*100}% per trade.")
        return v

config = Settings()
