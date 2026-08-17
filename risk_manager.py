"""Position sizing and trade parameter calculation engine."""
import math

class RiskManager:
    def __init__(self, risk_pct: float, contract_size: float = 100.0,
                 volume_min: float = 0.01, volume_max: float = 100.0, volume_step: float = 0.01):
        self.risk_pct = risk_pct
        self.contract_size = contract_size
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.volume_step = volume_step

    def calculate_lot_size(self, balance: float, entry_price: float, sl_price: float) -> float:
        """Calculates normalized lot size based on fixed fractional risk."""
        risk_capital = balance * self.risk_pct
        risk_per_ounce = abs(entry_price - sl_price)

        if risk_per_ounce <= 0:
            return self.volume_min

        # For XAUUSD: 1 Standard Lot = 100 oz. Risk per lot = risk_per_ounce * 100
        raw_lot = risk_capital / (risk_per_ounce * self.contract_size)
        
        # Normalize to step precision
        steps = math.floor(raw_lot / self.volume_step)
        normalized_lot = steps * self.volume_step
        return max(self.volume_min, min(self.volume_max, round(normalized_lot, 2)))

    def calculate_trade_levels(self, order_type: str, entry_price: float, atr: float,
                               atr_mult: float, tp1_r: float, tp2_r: float) -> dict:
        """Calculates SL, TP1, TP2, and Break-Even levels."""
        risk_dist = atr * atr_mult
        
        if order_type == "BUY":
            sl = round(entry_price - risk_dist, 2)
            tp1 = round(entry_price + (risk_dist * tp1_r), 2)
            tp2 = round(entry_price + (risk_dist * tp2_r), 2)
            be_price = round(entry_price + 0.10, 2)  # +$0.10 gold spread buffer
        else:
            sl = round(entry_price + risk_dist, 2)
            tp1 = round(entry_price - (risk_dist * tp1_r), 2)
            tp2 = round(entry_price - (risk_dist * tp2_r), 2)
            be_price = round(entry_price - 0.10, 2)

        return {"sl": sl, "tp1": tp1, "tp2": tp2, "be": be_price, "risk_dist": risk_dist}
