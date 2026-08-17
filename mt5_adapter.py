"""MetaTrader 5 API Bridge with retry resilience and partial trade handling."""
import time
from typing import Optional, List, Dict
import pandas as pd
import MetaTrader5 as mt5
from journal import logger

class MT5Adapter:
    def __init__(self, account: int, password: str, server: str, path: str, dry_run: bool = True):
        self.account = account
        self.password = password
        self.server = server
        self.path = path
        self.dry_run = dry_run

    def connect(self) -> bool:
        if not mt5.initialize(path=self.path, login=self.account, password=self.password, server=self.server):
            logger.error(f"MT5 Init failed: {mt5.last_error()}")
            return False
        logger.info(f"Connected to MT5 Server: {self.server} | Dry Run: {self.dry_run}")
        return True

    def disconnect(self):
        mt5.shutdown()
        logger.info("MT5 connection closed.")

    def get_market_data(self, symbol: str, timeframe: int, count: int = 300) -> Optional[pd.DataFrame]:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None or len(rates) == 0:
            logger.warning(f"Failed to fetch rates for {symbol}")
            return None
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    def get_symbol_info(self, symbol: str):
        return mt5.symbol_info(symbol)

    def get_account_balance(self) -> float:
        info = mt5.account_info()
        return info.equity if info else 0.0

    def get_open_positions(self, symbol: str, magic: int) -> List[Dict]:
        positions = mt5.positions_get(symbol=symbol)
        if positions is None:
            return []
        return [p._asdict() for p in positions if p.magic == magic]

    def execute_market_order(self, symbol: str, order_type: str, lot: float,
                             sl: float, tp: float, magic: int, slippage: int) -> Optional[int]:
        if self.dry_run:
            logger.info(f"[DRY RUN ORDER] {order_type} {lot} lots {symbol} @ MKT | SL: {sl} | TP: {tp}")
            return 999999

        tick = mt5.symbol_info_tick(symbol)
        price = tick.ask if order_type == "BUY" else tick.bid
        cmd = mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": cmd,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": slippage,
            "magic": magic,
            "comment": "Scalp_M5_Engine",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        for attempt in range(1, 4):
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Order #{result.order} executed successfully @ {result.price}")
                return result.order
            logger.warning(f"Order retry {attempt}/3 failed with code {result.retcode}: {result.comment}")
            time.sleep(1)

        logger.error("Failed to execute market order after retries.")
        return None

    def partial_close(self, position: Dict, volume_to_close: float) -> bool:
        if self.dry_run:
            logger.info(f"[DRY RUN] Partial close #{position['ticket']} vol: {volume_to_close}")
            return True

        cmd = mt5.ORDER_TYPE_SELL if position["type"] == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(position["symbol"]).bid if cmd == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(position["symbol"]).ask

        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": position["ticket"],
            "symbol": position["symbol"],
            "volume": volume_to_close,
            "type": cmd,
            "price": price,
            "magic": position["magic"],
            "comment": "Partial_TP1",
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        res = mt5.order_send(req)
        return res.retcode == mt5.TRADE_RETCODE_DONE

    def modify_sl(self, position: Dict, new_sl: float) -> bool:
        if self.dry_run:
            logger.info(f"[DRY RUN] SL adjusted for #{position['ticket']} to {new_sl}")
            return True

        req = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": position["ticket"],
            "symbol": position["symbol"],
            "sl": new_sl,
            "tp": position["tp"],
        }
        res = mt5.order_send(req)
        return res.retcode == mt5.TRADE_RETCODE_DONE

    def close_full_position(self, position: Dict, reason: str = "Emergency/News") -> bool:
        if self.dry_run:
            logger.info(f"[DRY RUN] Position #{position['ticket']} fully closed. Reason: {reason}")
            return True

        cmd = mt5.ORDER_TYPE_SELL if position["type"] == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(position["symbol"]).bid if cmd == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(position["symbol"]).ask

        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": position["ticket"],
            "symbol": position["symbol"],
            "volume": position["volume"],
            "type": cmd,
            "price": price,
            "magic": position["magic"],
            "comment": f"Close_{reason}",
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        res = mt5.order_send(req)
        return res.retcode == mt5.TRADE_RETCODE_DONE
