"""
Main Entrypoint for Binance Spot Phase 1 Live Paper Trading Scanner.
Integrates S3 (Closed Bar), I1 (Closed Bar), I2 (Momentum Ranker),
Market Safety Shield, 100 USDT Actionable Email Signals,
and Scheduled 12-Hour Activity Summaries (06:00 PKT & 18:00 PKT).
"""
import sys
import time
import argparse
from datetime import datetime, timezone, timedelta
from tabulate import tabulate
from colorama import init, Fore, Style

# Force UTF-8 on Windows stdout/stderr
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config.settings import (
    COINS_UNIVERSE, TIMEFRAME_S3, TIMEFRAME_I1_EXEC, TIMEFRAME_I1_TREND,
    TIMEFRAME_I2_RANK, SENDER_EMAIL, GMAIL_APP_PASSWORD, RECEIVER_EMAIL
)
from engine.binance_client import BinanceSpotClient
from engine.paper_broker import PaperBroker
from engine.state_manager import StateManager
from engine.safety_shield import MarketSafetyShield
from engine.time_utils import format_dual_time, get_pkt_hour, get_current_utc, PKT_OFFSET
from strategies.s3_volatility_squeeze import VolatilitySqueezeStrategy
from strategies.i1_mtf_trend_pullback import MultiTimeframePullbackStrategy
from strategies.i2_cross_sectional_momentum import CrossSectionalMomentumStrategy
from notifications.telegram_notifier import TelegramNotifier
from notifications.email_notifier import EmailNotifier
from reports.performance_tracker import PerformanceTracker
from engine.signal_queue import SignalQueue

init(autoreset=True)


class LiveScannerEngine:
    def __init__(self):
        self.client = BinanceSpotClient()
        self.state_manager = StateManager()
        self.broker = PaperBroker(self.state_manager)
        self.notifier = TelegramNotifier()
        self.email_notifier = EmailNotifier(
            sender_email=SENDER_EMAIL,
            app_password=GMAIL_APP_PASSWORD,
            receiver_email=RECEIVER_EMAIL
        )
        self.safety_shield = MarketSafetyShield()
        self.tracker = PerformanceTracker(self.broker)
        self.signal_queue = SignalQueue()
        
        # Initialize Phase 1 Strategies
        self.strat_s3 = VolatilitySqueezeStrategy()
        self.strat_i1 = MultiTimeframePullbackStrategy()
        self.strat_i2 = CrossSectionalMomentumStrategy(top_n=5)

    def check_and_send_12h_summary(self):
        """
        Checks if current time is within 06:00 PKT or 18:00 PKT window
        and dispatches 12-hour summary email if not already sent for this window.
        """
        now_utc = get_current_utc()
        now_pkt = now_utc + PKT_OFFSET
        current_hour_pkt = now_pkt.hour
        current_date_pkt = now_pkt.strftime("%Y-%m-%d")
        
        target_slot = None
        if current_hour_pkt in (6, 7):
            target_slot = f"{current_date_pkt}_06_AM"
        elif current_hour_pkt in (18, 19):
            target_slot = f"{current_date_pkt}_06_PM"
            
        if not target_slot:
            return

        last_slot = self.broker.state.get("last_12h_summary_slot")
        if last_slot == target_slot:
            return

        print(f"\n{Fore.CYAN}--> [12-HOUR TRIGGER] Dispatching 12-Hour Summary Report for {target_slot}...{Style.RESET_ALL}")
        summary_data = self.tracker.get_12h_summary_data(hours=12)
        
        sent = self.email_notifier.send_12h_summary_email(
            period_start_utc=summary_data["period_start_utc"],
            period_end_utc=summary_data["period_end_utc"],
            total_qualified=summary_data["total_qualified"],
            win_count=summary_data["win_count"],
            loss_count=summary_data["loss_count"],
            unresolved_count=summary_data["unresolved_count"],
            net_pnl_usdt=summary_data["net_pnl_usdt"],
            trades_details=summary_data["closed_trades"],
            open_positions_details=summary_data["open_positions"]
        )
        
        if sent:
            print(f"{Fore.GREEN}[OK] [12-HOUR SUMMARY SENT] Activity report delivered to {RECEIVER_EMAIL} ({target_slot}){Style.RESET_ALL}")
            self.broker.state["last_12h_summary_slot"] = target_slot
            self.broker.save()

    def run_scan_cycle(self):
        """Execute one complete scanning, safety evaluation, and trade management cycle."""
        now_str = format_dual_time()
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}[*] BINANCE SPOT SCAN CYCLE STARTED | {now_str}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        
        tickers = self.client.get_24h_tickers()
        if not tickers:
            print(f"{Fore.RED}[CRITICAL] Binance 24h tickers API returned empty after retries. Aborting this cycle to avoid false signals.{Style.RESET_ALL}")
            return
        current_prices = {sym: data["last_price"] for sym, data in tickers.items()}
        print(f"{Fore.GREEN}  [OK] Tickers loaded: {len(current_prices)} symbols.{Style.RESET_ALL}")
        
        # 1. Global Market Safety Shield Assessment
        print(f"\n{Fore.BLUE}--> Step 1: Evaluating Market Safety Shield & Timing Filters...{Style.RESET_ALL}")
        btc_15m = self.client.get_klines("BTCUSDT", "15m", limit=10)
        safety = self.safety_shield.evaluate_global_safety(btc_15m, tickers)
        
        if safety["timing_warning"]:
            print(f"{Fore.YELLOW}  [TIMING WARNING] {safety['timing_msg']}{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}  [TIMING CHECK] Normal market trading hours.{Style.RESET_ALL}")
            
        if not safety["is_safe"]:
            print(f"{Fore.RED}  [SAFETY TRIP] {safety['btc_msg']} | {safety['cascade_msg']}{Style.RESET_ALL}")
            print(f"{Fore.RED}  --> New Long Signals Blocked for this cycle to protect capital.{Style.RESET_ALL}")

        # 2. Update and Manage Existing Open Positions
        print(f"\n{Fore.BLUE}--> Step 2: Checking Active Positions ({len(self.broker.open_positions)} open)...{Style.RESET_ALL}")
        
        # P6: Active Position Capital Protection on BTC Flash Dump (>= 1.2% in 15m)
        if len(self.broker.open_positions) > 0:
            btc_15m = self.client.get_klines("BTCUSDT", "15m", limit=3)
            if not btc_15m.empty and len(btc_15m) >= 2:
                latest_btc = btc_15m.iloc[-1]
                btc_o = float(latest_btc['open'])
                btc_l = float(latest_btc['low'])
                btc_c = float(latest_btc['close'])
                btc_drop_pct = ((btc_l - btc_o) / btc_o) * 100.0
                
                if btc_drop_pct <= -1.2:
                    print(f"{Fore.RED}  [EMERGENCY TRIGGER] BTC Flash Dump detected ({btc_drop_pct:.2f}% drop in 15m candle)!{Style.RESET_ALL}")
                    tightened = self.broker.emergency_tighten_positions_to_breakeven()
                    if tightened:
                        last_alert_time = self.broker.state.get("last_emergency_dump_alert_time")
                        should_alert = True
                        if last_alert_time:
                            try:
                                last_dt = datetime.fromisoformat(last_alert_time.replace("Z", "+00:00"))
                                if (get_current_utc() - last_dt).total_seconds() < 1800:
                                    should_alert = False
                            except Exception:
                                pass
                        if should_alert:
                            self.broker.state["last_emergency_dump_alert_time"] = get_current_utc().isoformat()
                            self.broker.save()
                            email_sent = self.email_notifier.send_btc_emergency_dump_alert(
                                btc_drop_pct=abs(btc_drop_pct),
                                active_positions=tightened,
                                btc_price=btc_c
                            )
                            if email_sent:
                                print(f"{Fore.CYAN}    [EMAIL SENT] URGENT: BTC Flash Dump capital protection alert dispatched to {RECEIVER_EMAIL}{Style.RESET_ALL}")

        for symbol, pos in list(self.broker.open_positions.items()):
            curr_p = current_prices.get(symbol)
            if not curr_p:
                curr_p = self.client.get_current_price(symbol)
                
            if curr_p:
                current_prices[symbol] = curr_p
                df_15m = self.client.get_klines(symbol, "15m", limit=20)
                if not df_15m.empty:
                    # Filter candles that formed since the position was opened
                    entry_t = pos.get("entry_time")
                    df_candles = df_15m
                    if entry_t:
                        try:
                            import pandas as pd
                            entry_dt = pd.to_datetime(entry_t)
                            if entry_dt.tzinfo is not None:
                                entry_dt = entry_dt.tz_convert(None)
                            df_subset = df_15m[df_15m.index >= entry_dt]
                            if not df_subset.empty:
                                df_candles = df_subset
                        except Exception:
                            df_candles = df_15m
                            
                    period_high = float(df_candles['high'].max())
                    period_low = float(df_candles['low'].min())
                else:
                    period_high, period_low = curr_p, curr_p
                    
                event_data = self.broker.update_position_market_price(symbol, curr_p, period_high, period_low)
                if event_data:
                    if event_data.get("event") == "MILESTONE_TP1":
                        print(f"{Fore.GREEN}  [TP1 MILESTONE] {symbol} hit TP1 @ ${event_data['exit_price']:,.4f} | 50% Profit Locked: ${event_data['pnl_usdt']:+,.2f} | SL moved to Breakeven{Style.RESET_ALL}")
                    elif event_data.get("event") == "CLOSE":
                        trade = event_data["trade"]
                        pnl_color = Fore.GREEN if trade['net_pnl_usdt'] >= 0 else Fore.RED
                        print(f"{pnl_color}  [TRADE COMPLETED] {symbol} | Result: {trade['status']} ({trade['exit_reason']}) | Net PnL: ${trade['net_pnl_usdt']:+,.2f} ({trade['net_pnl_pct']:+.2f}%){Style.RESET_ALL}")
                        self.notifier.alert_close(
                            symbol=symbol,
                            strategy=trade["strategy"],
                            exit_price=trade.get("exit_price", curr_p),
                            pnl_usdt=trade["net_pnl_usdt"],
                            pnl_pct=trade["net_pnl_pct"],
                            reason=trade["exit_reason"]
                        )

        # 3. Evaluate Strategy I2: Cross-Sectional Momentum (1D Universe Rank)
        print(f"\n{Fore.BLUE}--> Step 3: Evaluating I2 Cross-Sectional Momentum (Top 50 Ranker)...{Style.RESET_ALL}")
        universe_1d = {}
        for symbol in COINS_UNIVERSE:
            df_1d = self.client.get_klines(symbol, TIMEFRAME_I2_RANK, limit=40)
            if not df_1d.empty and len(df_1d) >= 32:
                # Drop unclosed daily candle
                universe_1d[symbol] = df_1d.iloc[:-1] if len(df_1d) > 1 else df_1d
                
        btc_1d = universe_1d.get("BTCUSDT")
        top_coins, scores, btc_bullish = self.strat_i2.evaluate_universe(universe_1d, btc_1d)
        
        if not btc_bullish:
            print(f"{Fore.RED}  [BTC REGIME] BTC < 50-day SMA. Regime is Bearish -> 100% Cash Mode.{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}  [BTC REGIME] BTC > 50-day SMA (Bullish). Top Momentum Leaders: {', '.join(top_coins)}{Style.RESET_ALL}")

        # 4. Scan 50 Coins for Strategy Signals (S3 & I1 on COMPLETED CLOSED CANDLES)
        print(f"\n{Fore.BLUE}--> Step 4: Scanning 50 Coins for S3 (15m Squeeze) & I1 (1H Pullback) [Closed-Bar Evaluation]...{Style.RESET_ALL}")
        signals_found = 0

        if safety["is_safe"]:
            # ----------------------------------------------------------------
            # 4-PRE: Retry any previously queued signals (from failed cycles)
            # ----------------------------------------------------------------
            pending = self.signal_queue.get_valid_pending(current_prices)
            if pending:
                print(f"{Fore.YELLOW}  [QUEUE RETRY] {len(pending)} pending signal(s) from previous cycles — retrying now...{Style.RESET_ALL}")
            for sig in pending:
                symbol = sig["symbol"]
                curr_p = sig.get("current_price_now", current_prices.get(symbol))
                if not curr_p or not self.broker.can_open_position(symbol):
                    continue
                pos = self.broker.open_long_position(
                    symbol=symbol,
                    strategy_name=sig["strategy"],
                    current_price=curr_p,
                    stop_loss=sig["stop_loss"],
                    tp1=sig["tp1"],
                    tp2=sig["tp2"],
                    timeframe=sig.get("timeframe", "unknown"),
                    zone_candle_time=sig.get("zone_candle_time"),
                    metadata=sig.get("metadata")
                )
                if pos:
                    signals_found += 1
                    self.signal_queue.remove(symbol)
                    print(f"{Fore.GREEN}  [QUEUE BUY] {symbol} @ ${curr_p:,.4f} | SL: ${sig['stop_loss']:,.4f} | TP1: ${sig['tp1']:,.4f} | TP2: ${sig['tp2']:,.4f} [RETRIED FROM QUEUE]{Style.RESET_ALL}")
                    self.notifier.alert_buy(symbol, sig["strategy"], curr_p, sig["stop_loss"], sig["tp1"], sig["tp2"], sig.get("reason", "Queued signal retry"))
                    email_sent = self.email_notifier.send_trade_signal_email(
                        symbol=symbol,
                        strategy=sig["strategy"],
                        current_price=curr_p,
                        stop_loss=sig["stop_loss"],
                        tp1=sig["tp1"],
                        tp2=sig["tp2"],
                        reason=f"[QUEUED RETRY] {sig.get('reason', '')}",
                        metadata=sig.get("metadata"),
                        safety_info=safety,
                        candle_time=sig.get("zone_candle_time"),
                        timeframe=sig.get("timeframe", "unknown")
                    )
                    if email_sent:
                        print(f"{Fore.CYAN}    [EMAIL SENT] Queued signal executed — 100 USDT Actionable Plan dispatched to {RECEIVER_EMAIL}{Style.RESET_ALL}")

            # ----------------------------------------------------------------
            # 4-MAIN: Fresh scan of all 50 coins
            # ----------------------------------------------------------------
            for symbol in COINS_UNIVERSE:
                curr_p = current_prices.get(symbol)
                if not curr_p:
                    # Fallback: fetch individual price if bulk tickers missed this symbol
                    curr_p = self.client.get_current_price(symbol)
                    if curr_p:
                        current_prices[symbol] = curr_p
                if not curr_p:
                    continue

                if not self.broker.can_open_position(symbol):
                    continue

                # 4A. Evaluate S3: 15m Volatility Squeeze on COMPLETED closed candle with 1H Trend Confluence
                df_15m = self.client.get_klines(symbol, TIMEFRAME_S3, limit=65)
                if not df_15m.empty and len(df_15m) >= 50:
                    closed_15m = df_15m.iloc[:-1]
                    df_1h_check = self.client.get_klines(symbol, "1h", limit=30)
                    closed_1h = df_1h_check.iloc[:-1] if not df_1h_check.empty and len(df_1h_check) >= 25 else None
                    s3_signal = self.strat_s3.evaluate(symbol, closed_15m, df_1h=closed_1h)
                    if s3_signal and s3_signal.action == "BUY":
                        signals_found += 1
                        zone_time = closed_15m.index[-1].isoformat()
                        pos = self.broker.open_long_position(
                            symbol=symbol,
                            strategy_name=s3_signal.strategy_name,
                            current_price=curr_p,
                            stop_loss=s3_signal.stop_loss,
                            tp1=s3_signal.tp1,
                            tp2=s3_signal.tp2,
                            timeframe="15m",
                            zone_candle_time=zone_time,
                            metadata=s3_signal.metadata
                        )
                        if pos:
                            self.signal_queue.remove(symbol)  # Clear any old queue entry
                            print(f"{Fore.GREEN}  [BUY S3] {symbol} @ ${curr_p:,.4f} | SL: ${s3_signal.stop_loss:,.4f} | TP1: ${s3_signal.tp1:,.4f} | TP2: ${s3_signal.tp2:,.4f}{Style.RESET_ALL}")
                            self.notifier.alert_buy(symbol, s3_signal.strategy_name, curr_p, s3_signal.stop_loss, s3_signal.tp1, s3_signal.tp2, s3_signal.reason)
                            email_sent = self.email_notifier.send_trade_signal_email(
                                symbol=symbol,
                                strategy=s3_signal.strategy_name,
                                current_price=curr_p,
                                stop_loss=s3_signal.stop_loss,
                                tp1=s3_signal.tp1,
                                tp2=s3_signal.tp2,
                                reason=s3_signal.reason,
                                metadata=s3_signal.metadata,
                                safety_info=safety,
                                candle_time=zone_time,
                                timeframe="15m"
                            )
                            if email_sent:
                                print(f"{Fore.CYAN}    [EMAIL SENT] 100 USDT Actionable Plan dispatched to {RECEIVER_EMAIL}{Style.RESET_ALL}")
                        else:
                            # Execution failed — save to queue for next cycle
                            self.signal_queue.enqueue({
                                "symbol": symbol, "strategy": s3_signal.strategy_name,
                                "entry_price": curr_p, "stop_loss": s3_signal.stop_loss,
                                "tp1": s3_signal.tp1, "tp2": s3_signal.tp2,
                                "timeframe": "15m", "zone_candle_time": zone_time,
                                "reason": s3_signal.reason, "metadata": s3_signal.metadata
                            })
                        continue

                # 4B. Evaluate I1: MTF Pullback (4H Trend + 1H Execution) on COMPLETED closed candles
                df_1h = self.client.get_klines(symbol, TIMEFRAME_I1_EXEC, limit=85)
                df_4h = self.client.get_klines(symbol, TIMEFRAME_I1_TREND, limit=225)

                if not df_1h.empty and not df_4h.empty and len(df_1h) >= 60 and len(df_4h) >= 220:
                    closed_1h = df_1h.iloc[:-1]
                    closed_4h = df_4h.iloc[:-1]
                    i1_signal = self.strat_i1.evaluate(symbol, closed_1h, df_4h=closed_4h)
                    if i1_signal and i1_signal.action == "BUY":
                        signals_found += 1
                        zone_time = closed_1h.index[-1].isoformat()
                        pos = self.broker.open_long_position(
                            symbol=symbol,
                            strategy_name=i1_signal.strategy_name,
                            current_price=curr_p,
                            stop_loss=i1_signal.stop_loss,
                            tp1=i1_signal.tp1,
                            tp2=i1_signal.tp2,
                            timeframe="1h (4h Macro Trend)",
                            zone_candle_time=zone_time,
                            metadata=i1_signal.metadata
                        )
                        if pos:
                            self.signal_queue.remove(symbol)  # Clear any old queue entry
                            print(f"{Fore.GREEN}  [BUY I1] {symbol} @ ${curr_p:,.4f} | SL: ${i1_signal.stop_loss:,.4f} | TP1: ${i1_signal.tp1:,.4f} | TP2: ${i1_signal.tp2:,.4f}{Style.RESET_ALL}")
                            self.notifier.alert_buy(symbol, i1_signal.strategy_name, curr_p, i1_signal.stop_loss, i1_signal.tp1, i1_signal.tp2, i1_signal.reason)
                            email_sent = self.email_notifier.send_trade_signal_email(
                                symbol=symbol,
                                strategy=i1_signal.strategy_name,
                                current_price=curr_p,
                                stop_loss=i1_signal.stop_loss,
                                tp1=i1_signal.tp1,
                                tp2=i1_signal.tp2,
                                reason=i1_signal.reason,
                                metadata=i1_signal.metadata,
                                safety_info=safety,
                                candle_time=zone_time,
                                timeframe="1h (4h Macro Trend)"
                            )
                            if email_sent:
                                print(f"{Fore.CYAN}    [EMAIL SENT] 100 USDT Actionable Plan dispatched to {RECEIVER_EMAIL}{Style.RESET_ALL}")
                        else:
                            # Execution failed — save to queue for next cycle
                            self.signal_queue.enqueue({
                                "symbol": symbol, "strategy": i1_signal.strategy_name,
                                "entry_price": curr_p, "stop_loss": i1_signal.stop_loss,
                                "tp1": i1_signal.tp1, "tp2": i1_signal.tp2,
                                "timeframe": "1h (4h Macro Trend)", "zone_candle_time": zone_time,
                                "reason": i1_signal.reason, "metadata": i1_signal.metadata
                            })

        print(f"{Fore.MAGENTA}  Scanning complete. New Signals Executed: {signals_found} | Pending Queue: {len(self.signal_queue)}{Style.RESET_ALL}")

        # 5. Check 12-Hour Summary Schedule (06:00 PKT / 18:00 PKT)
        self.check_and_send_12h_summary()

        # 6. Compute Metrics & Save LIVE_RESULTS.md
        print(f"\n{Fore.BLUE}--> Step 5: Updating LIVE_RESULTS.md and Performance Scorecard...{Style.RESET_ALL}")
        self.tracker.save_live_results(current_prices)
        metrics = self.tracker.compute_metrics(current_prices)
        
        print(f"{Fore.GREEN}[OK] Live Dashboard updated successfully. Current Equity: ${metrics['current_equity']:,.2f} USDT | Return: {metrics['total_return_pct']:+.2f}%{Style.RESET_ALL}\n")

    def print_report(self):
        """Print console performance summary."""
        tickers = self.client.get_24h_tickers()
        current_prices = {sym: data["last_price"] for sym, data in tickers.items()}
        metrics = self.tracker.compute_metrics(current_prices)
        
        summary_table = [
            ["Starting Balance", f"${metrics['starting_balance']:,.2f} USDT"],
            ["Current Equity", f"${metrics['current_equity']:,.2f} USDT"],
            ["Available Cash", f"${metrics['cash_usdt']:,.2f} USDT"],
            ["Net PnL ($)", f"${metrics['total_pnl_usdt']:+,.2f} USDT"],
            ["Net Return (%)", f"{metrics['total_return_pct']:+.2f}%"],
            ["Total Qualified Trades", f"{metrics['total_qualified_trades']} Unique Trades"],
            ["Completed Trades", f"{metrics['completed_trades_count']} Trades"],
            ["Active In-Trade", f"{metrics['active_trades_count']} Trade"],
            ["Win Rate", f"{metrics['win_rate']:.2f}% ({metrics['win_count']}W / {metrics['loss_count']}L)"],
            ["Profit Factor", f"{metrics['profit_factor']:.2f}"],
            ["Max Drawdown", f"-{metrics['max_drawdown_pct']:.2f}%"],
            ["Total Fees Deducted", f"${metrics['total_fees_paid']:,.2f} USDT"],
            ["Report Time", format_dual_time()]
        ]
        print(f"\n{Fore.YELLOW}=== 📊 15-DAY LIVE PAPER TRADING PERFORMANCE REPORT ==={Style.RESET_ALL}")
        print(tabulate(summary_table, headers=["Metric", "Value"], tablefmt="fancy_grid"))


def main():
    parser = argparse.ArgumentParser(description="Binance Spot Phase 1 Live Paper Trading Scanner")
    parser.add_argument("--mode", choices=["scan", "live-paper", "report", "test-email", "test-summary"], default="scan",
                        help="Execution mode: 'scan', 'live-paper', 'report', 'test-email', 'test-summary'")
    parser.add_argument("--interval", type=int, default=60, help="Interval in seconds for continuous mode (default: 60s)")
    args = parser.parse_args()

    engine = LiveScannerEngine()

    if args.mode == "test-email":
        print(f"{Fore.CYAN}Sending Test Actionable 100 USDT Signal Email to {RECEIVER_EMAIL}...{Style.RESET_ALL}")
        sent = engine.email_notifier.send_trade_signal_email(
            symbol="SOLUSDT",
            strategy="I1_MTF_TREND_PULLBACK",
            current_price=142.50,
            stop_loss=137.90,
            tp1=147.50,
            tp2=154.00,
            reason="[TEST SCAN] 4H Macro Trend Bullish + 1H EMA21 Pullback Reversal",
            safety_info={"timing_msg": "Normal market trading hours."},
            candle_time=get_current_utc() - timedelta(minutes=15)
        )
        if sent:
            print(f"{Fore.GREEN}[SUCCESS] Test email successfully delivered to {RECEIVER_EMAIL}!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[FAILED] Email delivery failed.{Style.RESET_ALL}")
            
    elif args.mode == "test-summary":
        print(f"{Fore.CYAN}Sending Test 12-Hour Activity Summary Email to {RECEIVER_EMAIL}...{Style.RESET_ALL}")
        summary_data = engine.tracker.get_12h_summary_data(hours=12)
        sent = engine.email_notifier.send_12h_summary_email(
            period_start_utc=summary_data["period_start_utc"],
            period_end_utc=summary_data["period_end_utc"],
            total_qualified=summary_data["total_qualified"],
            win_count=summary_data["win_count"],
            loss_count=summary_data["loss_count"],
            unresolved_count=summary_data["unresolved_count"],
            net_pnl_usdt=summary_data["net_pnl_usdt"],
            trades_details=summary_data["closed_trades"],
            open_positions_details=summary_data["open_positions"]
        )
        if sent:
            print(f"{Fore.GREEN}[SUCCESS] 12-Hour Summary Email successfully delivered to {RECEIVER_EMAIL}! Please check your Inbox.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[FAILED] 12-Hour Summary Email delivery failed.{Style.RESET_ALL}")
            
    elif args.mode == "scan":
        engine.run_scan_cycle()
    elif args.mode == "report":
        engine.print_report()
    elif args.mode == "live-paper":
        print(f"{Fore.GREEN}Starting Continuous Live Paper Trading Daemon (Interval: {args.interval}s). Press Ctrl+C to stop.{Style.RESET_ALL}")
        while True:
            try:
                engine.run_scan_cycle()
                time.sleep(args.interval)
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Daemon stopped by user.{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"{Fore.RED}Unexpected error in cycle: {e}{Style.RESET_ALL}")
                time.sleep(10)


if __name__ == "__main__":
    main()
