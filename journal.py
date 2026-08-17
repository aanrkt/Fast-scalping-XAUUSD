"""Trade journaling system backed by SQLite and structured logging."""
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("XAUUSD_Scalper")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}'
    )

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    fh = RotatingFileHandler("trading_bot.log", maxBytes=10*1024*1024, backupCount=5)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger

logger = setup_logger()

class TradeJournal:
    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    ticket INTEGER PRIMARY KEY,
                    symbol TEXT,
                    order_type TEXT,
                    lot REAL,
                    open_price REAL,
                    sl REAL,
                    tp1 REAL,
                    tp2 REAL,
                    open_time TEXT,
                    close_price REAL,
                    close_time TEXT,
                    pnl REAL,
                    partial_done INTEGER DEFAULT 0,
                    status TEXT
                )
            """)
            conn.commit()

    def log_entry(self, ticket: int, symbol: str, order_type: str, lot: float,
                  open_price: float, sl: float, tp1: float, tp2: float):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO trades 
                (ticket, symbol, order_type, lot, open_price, sl, tp1, tp2, open_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
            """, (ticket, symbol, order_type, lot, open_price, sl, tp1, tp2, datetime.utcnow().isoformat()))
            conn.commit()

    def update_partial_status(self, ticket: int, partial_done: bool):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE trades SET partial_done = ? WHERE ticket = ?", (1 if partial_done else 0, ticket))
            conn.commit()

    def log_exit(self, ticket: int, close_price: float, pnl: float, status: str = "CLOSED"):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE trades 
                SET close_price = ?, close_time = ?, pnl = ?, status = ?
                WHERE ticket = ?
            """, (close_price, datetime.utcnow().isoformat(), pnl, status, ticket))
            conn.commit()
