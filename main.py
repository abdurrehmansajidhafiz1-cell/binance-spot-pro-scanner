"""
Main Entrypoint for Binance Spot Phase 1 Live Paper Trading Scanner.
Integrates S3 (15m Squeeze), I1 (MTF Pullback), I2 (Momentum Ranker),
Market Safety Shield, and 100 USDT Actionable Email Notifications.
"""
import sys
import time
import argparse
from datetime import datetime, timezone
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
from strategies.s3_volatility_squeeze import VolatilitySqueezeStrategy
from strategies.i1_mtf_trend_pullback import MultiTimeframePullbackStrategy
from strategies.i2_cross_sectional_momentum import CrossSectionalMomentumStrategy
from notifications.telegram_notifier import TelegramNotifier
from notifications.email_notifier import EmailNotifier
from reports.performance_tracker import PerformanceTracker

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
        
        # Initialize Phase 1 Strategies
        self.strat_s3 = VolatilitySqueezeStrategy()
        self.strat_i1 = MultiTimeframePullbackStrategy()
        self.strat_i2 = CrossSectionalMomentumStrategy(top_n=5)

    def run_scan_cycle(self):
        """Execute one complete scanning, safety evaluation, and trade management cycle."""
        now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}[*] BINANCE SPOT SCAN CYCLE STARTED | {now_str}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        
        tickers = self.client.get_24h_tickers()
        current_prices = {sym: data["last_price"] for sym, data in tickers.items()}
        
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
        for symbol, pos in list(self.broker.open_positions.items()):
            curr_p = current_prices.get(symbol)
            if not curr_p:
                curr_p = self.client.get_current_price(symbol)
                
            if curr_p:
                current_prices[symbol] = curr_p
                df_15m = self.client.get_klines(symbol, "15m", limit=3)
                if not df_15m.empty:
                    last_high = float(df_15m['high'].iloc[-1])
                    last_low = float(df_15m['low'].iloc[-1])
                else:
                    last_high, last_low = curr_p, curr_p
                    
                trade_record = self.broker.update_position_market_price(symbol, curr_p, last_high, last_low)
                if trade_record:
                    pnl_color = Fore.GREEN if trade_record['net_pnl_usdt'] >= 0 else Fore.RED
                    print(f"{pnl_color}  [CLOSED] {symbol} | Reason: {trade_record['exit_reason']} | PnL: ${trade_record['net_pnl_usdt']:+,.2f} ({trade_record['net_pnl_pct']:+.2f}%){Style.RESET_ALL}")
                    self.notifier.alert_close(
                        symbol=symbol,
                        strategy=trade_record["strategy"],
                        exit_price=trade_record["exit_price"],
                        pnl_usdt=trade_record["net_pnl_usdt"],
                        pnl_pct=trade_record["net_pnl_pct"],
                        reason=trade_record["exit_reason"]
                    )

        # 3. Evaluate Strategy I2: Cross-Sectional Momentum (1D Universe Rank)
        print(f"\n{Fore.BLUE}--> Step 3: Evaluating I2 Cross-Sectional Momentum (Top 50 Ranker)...{Style.RESET_ALL}")
        universe_1d = {}
        for symbol in COINS_UNIVERSE:
            df_1d = self.client.get_klines(symbol, TIMEFRAME_I2_RANK, limit=40)
            if not df_1d.empty and len(df_1d) >= 32:
                universe_1d[symbol] = df_1d
                
        btc_1d = universe_1d.get("BTCUSDT")
        top_coins, scores, btc_bullish = self.strat_i2.evaluate_universe(universe_1d, btc_1d)
        
        if not btc_bullish:
            print(f"{Fore.RED}  [BTC REGIME] BTC < 50-day SMA. Regime is Bearish -> 100% Cash Mode.{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}  [BTC REGIME] BTC > 50-day SMA (Bullish). Top Momentum Leaders: {', '.join(top_coins)}{Style.RESET_ALL}")

        # 4. Scan 50 Coins for Strategy Signals (S3 & I1)
        print(f"\n{Fore.BLUE}--> Step 4: Scanning 50 Coins for S3 (15m Squeeze) & I1 (1H Pullback)...{Style.RESET_ALL}")
        signals_found = 0
        
        if safety["is_safe"]:
            for symbol in COINS_UNIVERSE:
                curr_p = current_prices.get(symbol)
                if not curr_p:
                    continue
                    
                if not self.broker.can_open_position(symbol):
                    continue

                # Evaluate S3: 15m Volatility Squeeze
                df_15m = self.client.get_klines(symbol, TIMEFRAME_S3, limit=60)
                if not df_15m.empty:
                    s3_signal = self.strat_s3.evaluate(symbol, df_15m)
                    if s3_signal and s3_signal.action == "BUY":
                        signals_found += 1
                        pos = self.broker.open_long_position(
                            symbol=symbol,
                            strategy_name=s3_signal.strategy_name,
                            current_price=s3_signal.price,
                            stop_loss=s3_signal.stop_loss,
                            tp1=s3_signal.tp1,
                            tp2=s3_signal.tp2,
                            metadata=s3_signal.metadata
                        )
                        if pos:
                            print(f"{Fore.GREEN}  [BUY S3] {symbol} @ ${s3_signal.price:,.4f} | SL: ${s3_signal.stop_loss:,.4f} | TP1: ${s3_signal.tp1:,.4f} | TP2: ${s3_signal.tp2:,.4f}{Style.RESET_ALL}")
                            # Send Telegram & Comprehensive 100 USDT Email Alert
                            self.notifier.alert_buy(symbol, s3_signal.strategy_name, s3_signal.price, s3_signal.stop_loss, s3_signal.tp1, s3_signal.tp2, s3_signal.reason)
                            email_sent = self.email_notifier.send_trade_signal_email(
                                symbol=symbol,
                                strategy=s3_signal.strategy_name,
                                current_price=s3_signal.price,
                                stop_loss=s3_signal.stop_loss,
                                tp1=s3_signal.tp1,
                                tp2=s3_signal.tp2,
                                reason=s3_signal.reason,
                                metadata=s3_signal.metadata,
                                safety_info=safety
                            )
                            if email_sent:
                                print(f"{Fore.CYAN}    [EMAIL SENT] 100 USDT Actionable Plan dispatched to {RECEIVER_EMAIL}{Style.RESET_ALL}")
                            continue

                # Evaluate I1: MTF Pullback (4H Trend + 1H Execution)
                df_1h = self.client.get_klines(symbol, TIMEFRAME_I1_EXEC, limit=80)
                df_4h = self.client.get_klines(symbol, TIMEFRAME_I1_TREND, limit=220)
                
                if not df_1h.empty and not df_4h.empty:
                    i1_signal = self.strat_i1.evaluate(symbol, df_1h, df_4h=df_4h)
                    if i1_signal and i1_signal.action == "BUY":
                        signals_found += 1
                        pos = self.broker.open_long_position(
                            symbol=symbol,
                            strategy_name=i1_signal.strategy_name,
                            current_price=i1_signal.price,
                            stop_loss=i1_signal.stop_loss,
                            tp1=i1_signal.tp1,
                            tp2=i1_signal.tp2,
                            metadata=i1_signal.metadata
                        )
                        if pos:
                            print(f"{Fore.GREEN}  [BUY I1] {symbol} @ ${i1_signal.price:,.4f} | SL: ${i1_signal.stop_loss:,.4f} | TP1: ${i1_signal.tp1:,.4f} | TP2: ${i1_signal.tp2:,.4f}{Style.RESET_ALL}")
                            # Send Telegram & Comprehensive 100 USDT Email Alert
                            self.notifier.alert_buy(symbol, i1_signal.strategy_name, i1_signal.price, i1_signal.stop_loss, i1_signal.tp1, i1_signal.tp2, i1_signal.reason)
                            email_sent = self.email_notifier.send_trade_signal_email(
                                symbol=symbol,
                                strategy=i1_signal.strategy_name,
                                current_price=i1_signal.price,
                                stop_loss=i1_signal.stop_loss,
                                tp1=i1_signal.tp1,
                                tp2=i1_signal.tp2,
                                reason=i1_signal.reason,
                                metadata=i1_signal.metadata,
                                safety_info=safety
                            )
                            if email_sent:
                                print(f"{Fore.CYAN}    [EMAIL SENT] 100 USDT Actionable Plan dispatched to {RECEIVER_EMAIL}{Style.RESET_ALL}")

        print(f"{Fore.MAGENTA}  Scanning complete. New Signals Executed: {signals_found}{Style.RESET_ALL}")

        # 5. Compute Metrics & Save LIVE_RESULTS.md
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
            ["Total Realized Trades", f"{metrics['total_trades']}"],
            ["Win Rate", f"{metrics['win_rate']:.2f}% ({metrics['win_count']}W / {metrics['loss_count']}L)"],
            ["Profit Factor", f"{metrics['profit_factor']:.2f}"],
            ["Max Drawdown", f"-{metrics['max_drawdown_pct']:.2f}%"],
            ["Total Fees Deducted", f"${metrics['total_fees_paid']:,.2f} USDT"],
            ["Active Positions", f"{metrics['open_positions_count']}"]
        ]
        print(f"\n{Fore.YELLOW}=== 📊 15-DAY LIVE PAPER TRADING PERFORMANCE REPORT ==={Style.RESET_ALL}")
        print(tabulate(summary_table, headers=["Metric", "Value"], tablefmt="fancy_grid"))


def main():
    parser = argparse.ArgumentParser(description="Binance Spot Phase 1 Live Paper Trading Scanner")
    parser.add_argument("--mode", choices=["scan", "live-paper", "report", "test-email"], default="scan",
                        help="Execution mode: 'scan', 'live-paper', 'report', 'test-email'")
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
            safety_info={"timing_msg": "Normal market trading hours."}
        )
        if sent:
            print(f"{Fore.GREEN}[SUCCESS] Test email successfully delivered to {RECEIVER_EMAIL}! Please check your Inbox / Spam folder.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[FAILED] Email delivery failed. Please verify credentials.{Style.RESET_ALL}")
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
