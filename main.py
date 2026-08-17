"""Main orchestrator for XAUUSD M5 trading bot."""
import sys
import time
import signal
import MetaTrader5 as mt5
from config import config
from journal import logger, TradeJournal
from news_filter import NewsFilter
from strategy import StrategyEngine
from risk_manager import RiskManager
from mt5_adapter import MT5Adapter

running = True

def handle_shutdown(sig, frame):
    global running
    logger.info("Shutdown signal received. Completing loop and closing...")
    running = False

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

def main():
    global running
    journal = TradeJournal()
    news = NewsFilter(pre_news_buffer_mins=30, post_news_buffer_mins=30)
    
    adapter = MT5Adapter(
        account=config.MT5_ACCOUNT,
        password=config.MT5_PASSWORD,
        server=config.MT5_SERVER,
        path=config.MT5_PATH,
        dry_run=config.DRY_RUN
    )

    if not adapter.connect():
        sys.exit(1)

    sym_info = adapter.get_symbol_info(config.SYMBOL)
    if not sym_info:
        logger.error(f"Symbol {config.SYMBOL} not found.")
        adapter.disconnect()
        sys.exit(1)

    risk_mgr = RiskManager(
        risk_pct=config.RISK_PER_TRADE_PCT,
        contract_size=sym_info.trade_contract_size,
        volume_min=sym_info.volume_min,
        volume_max=sym_info.volume_max,
        volume_step=sym_info.volume_step
    )

    logger.info(f"Engine running. Symbol: {config.SYMBOL} | TF: {config.TIMEFRAME} | Safe Mode: {config.DRY_RUN}")

    tracked_trade = {}  # In-memory tracking for partial TP state

    while running:
        try:
            # 1. News Protection Logic
            if news.is_imminent_news(window_mins=15):
                open_pos = adapter.get_open_positions(config.SYMBOL, config.MAGIC_NUMBER)
                for pos in open_pos:
                    t_id = pos["ticket"]
                    if not tracked_trade.get(t_id, {}).get("partial_done", False):
                        logger.warning(f"Closing trade #{t_id} before High-Impact News.")
                        if adapter.close_full_position(pos, reason="PreNewsRisk"):
                            journal.log_exit(t_id, pos["price_current"], pos["profit"], "CLOSED_NEWS")

            # 2. Manage Active Positions (Partial TP & BE)
            open_positions = adapter.get_open_positions(config.SYMBOL, config.MAGIC_NUMBER)
            for pos in open_positions:
                t_id = pos["ticket"]
                state = tracked_trade.get(t_id)

                if state and not state.get("partial_done", False):
                    curr_p = pos["price_current"]
                    is_buy = pos["type"] == mt5.ORDER_TYPE_BUY
                    hit_tp1 = (curr_p >= state["tp1"]) if is_buy else (curr_p <= state["tp1"])

                    if hit_tp1:
                        logger.info(f"Target 1.2R reached for #{t_id}. Executing 50% partial profit.")
                        close_vol = round(pos["volume"] * config.PARTIAL_CLOSE_RATIO, 2)
                        if adapter.partial_close(pos, close_vol):
                            adapter.modify_sl(pos, state["be"])
                            state["partial_done"] = True
                            journal.update_partial_status(t_id, True)
                            logger.info(f"SL moved to Break-Even ({state['be']}) for #{t_id}")

            # 3. New Entry Evaluation
            if len(open_positions) < config.MAX_CONCURRENT_POSITIONS:
                if not news.is_news_blocked():
                    df = adapter.get_market_data(config.SYMBOL, mt5.TIMEFRAME_M5, count=250)
                    if df is not None:
                        df = StrategyEngine.calculate_indicators(df)
                        signal_type = StrategyEngine.evaluate_signal(df)

                        if signal_type in ["BUY", "SELL"]:
                            latest_close = df.iloc[-2]["close"]
                            latest_atr = df.iloc[-2]["atr"]
                            levels = risk_mgr.calculate_trade_levels(
                                signal_type, latest_close, latest_atr,
                                config.ATR_MULTIPLIER, config.TP1_R_MULTIPLE, config.TP2_R_MULTIPLE
                            )
                            balance = adapter.get_account_balance()
                            lot = risk_mgr.calculate_lot_size(balance, latest_close, levels["sl"])

                            ticket = adapter.execute_market_order(
                                config.SYMBOL, signal_type, lot, levels["sl"], levels["tp2"],
                                config.MAGIC_NUMBER, config.SLIPPAGE_POINTS
                            )

                            if ticket:
                                tracked_trade[ticket] = {
                                    "tp1": levels["tp1"],
                                    "be": levels["be"],
                                    "partial_done": False
                                }
                                journal.log_entry(ticket, config.SYMBOL, signal_type, lot,
                                                  latest_close, levels["sl"], levels["tp1"], levels["tp2"])
                else:
                    logger.debug("Trade execution blocked by News Filter.")

            time.sleep(1)

        except Exception as e:
            logger.error(f"Unexpected error in event loop: {str(e)}", exc_info=True)
            time.sleep(5)

    adapter.disconnect()

if __name__ == "__main__":
    main()
