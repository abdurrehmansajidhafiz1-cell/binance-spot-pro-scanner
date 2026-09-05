"""
Email Notification Service for Binance Spot Trading Signals & 12-Hour Summaries.
Supports dual timestamps (Pakistan Standard Time PKT + UTC) and comprehensive trade plans.
"""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from engine.time_utils import format_dual_time, get_current_utc


class EmailNotifier:
    def __init__(self, sender_email: Optional[str] = None, app_password: Optional[str] = None, receiver_email: Optional[str] = None):
        self.sender_email = (sender_email or os.getenv("SENDER_EMAIL", "")).strip()
        self.app_password = (app_password or os.getenv("GMAIL_APP_PASSWORD", "")).replace(" ", "").strip()
        self.receiver_email = (receiver_email or os.getenv("RECEIVER_EMAIL", "")).strip()
        self.enabled = bool(self.sender_email and self.app_password and self.receiver_email)

    def send_email(self, subject: str, html_content: str, text_content: str) -> bool:
        if not self.enabled:
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Binance Spot Scanner <{self.sender_email}>"
        msg["To"] = self.receiver_email

        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        msg.attach(part1)
        msg.attach(part2)

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=12) as server:
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, self.receiver_email, msg.as_string())
            return True
        except Exception:
            try:
                with smtplib.SMTP("smtp.gmail.com", 587, timeout=12) as server:
                    server.starttls()
                    server.login(self.sender_email, self.app_password)
                    server.sendmail(self.sender_email, self.receiver_email, msg.as_string())
                return True
            except Exception as e_fallback:
                print(f"[ERROR] Failed to send email via SMTP: {e_fallback}")
                return False

    def send_trade_signal_email(self, symbol: str, strategy: str, current_price: float,
                                stop_loss: float, tp1: float, tp2: float,
                                reason: str, metadata: Optional[Dict[str, Any]] = None,
                                safety_info: Optional[Dict[str, Any]] = None,
                                candle_time: Optional[Any] = None,
                                timeframe: str = "15m") -> bool:
        """
        Formats and dispatches a comprehensive, actionable 100 USDT trade execution plan with dual PKT + UTC timestamps
        and exact TradingView chart timeframe.
        """
        signal_time_str = format_dual_time()
        candle_time_str = format_dual_time(candle_time) if candle_time else signal_time_str
        capital_usdt = 100.0
        
        # Calculate Risk and Sizing
        risk_pct = ((current_price - stop_loss) / current_price) * 100.0
        max_loss_usdt = (capital_usdt * (risk_pct / 100.0))
        tp1_gain_pct = ((tp1 - current_price) / current_price) * 100.0
        tp2_gain_pct = ((tp2 - current_price) / current_price) * 100.0
        
        # Entry Plan Logic based on Strategy
        if "I1" in strategy:
            entry1_usdt = 60.0
            entry1_price = current_price
            entry1_qty = entry1_usdt / entry1_price
            
            entry2_usdt = 40.0
            entry2_price = current_price * 0.988 # 1.2% deeper dip order
            entry2_qty = entry2_usdt / entry2_price
            
            entry_style_text = (
                f"• Entry 1 (Market Order — $60.00 USDT): Buy at ${entry1_price:,.4f} (~{entry1_qty:.4f} {symbol[:-4]})\n"
                f"• Entry 2 (Limit Order — $40.00 USDT): Place Limit Buy at deeper dip ${entry2_price:,.4f} (~{entry2_qty:.4f} {symbol[:-4]})\n"
                f"• Average Expected Entry: ~${(entry1_usdt + entry2_usdt) / (entry1_qty + entry2_qty):,.4f}"
            )
            entry_style_html = f"""
            <table style="width:100%; border-collapse: collapse; margin-top: 8px;">
                <tr style="background:#f1f5f9;">
                    <th style="padding:8px; border:1px solid #cbd5e1; text-align:left;">Order Type</th>
                    <th style="padding:8px; border:1px solid #cbd5e1; text-align:left;">Amount (USDT)</th>
                    <th style="padding:8px; border:1px solid #cbd5e1; text-align:left;">Target Price</th>
                    <th style="padding:8px; border:1px solid #cbd5e1; text-align:left;">Est. Quantity</th>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #cbd5e1;"><b>Market Buy (60%)</b></td>
                    <td style="padding:8px; border:1px solid #cbd5e1;">$60.00 USDT</td>
                    <td style="padding:8px; border:1px solid #cbd5e1;"><b>${entry1_price:,.4f}</b></td>
                    <td style="padding:8px; border:1px solid #cbd5e1;">{entry1_qty:.4f}</td>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #cbd5e1;"><b>Limit Dip Buy (40%)</b></td>
                    <td style="padding:8px; border:1px solid #cbd5e1;">$40.00 USDT</td>
                    <td style="padding:8px; border:1px solid #cbd5e1;"><b>${entry2_price:,.4f}</b></td>
                    <td style="padding:8px; border:1px solid #cbd5e1;">{entry2_qty:.4f}</td>
                </tr>
            </table>
            """
        elif "I2" in strategy:
            entry_style_text = (
                f"• Basket Momentum Allocation ($20.00 USDT per coin across Top 5 Leaders)\n"
                f"• Buy $20.00 USDT at current price ${current_price:,.4f} (~{20.0/current_price:.4f} {symbol[:-4]})"
            )
            entry_style_html = f"<p><b>Basket Allocation:</b> Buy <b>$20.00 USDT</b> of this coin at market price <b>${current_price:,.4f}</b> as part of Top 5 Momentum Leaders.</p>"
        else:
            qty_100 = capital_usdt / current_price
            entry_style_text = f"• Single Market Entry: Buy 100% ($100.00 USDT) at ${current_price:,.4f} (~{qty_100:.4f} {symbol[:-4]})"
            entry_style_html = f"<p><b>Fast Breakout Entry:</b> Buy 100% (<b>$100.00 USDT</b>) at current price <b>${current_price:,.4f}</b> (~{qty_100:.4f} {symbol[:-4]}).</p>"

        be_price = current_price * 1.0025
        subject = f"🟢 [BINANCE SPOT SIGNAL] {symbol} ({timeframe}) | Strategy: {strategy} | Capital: $100 USDT"

        text_content = f"""
================================================================================
BINANCE SPOT TRADE EXECUTION PLAN — {symbol}
================================================================================
• TradingView Timeframe: {timeframe}  <-- Open this timeframe on TradingView
• Signal Time:        {signal_time_str}
• Zone / Candle Time: {candle_time_str}
• Strategy:           {strategy}
• Total Capital:      $100.00 USDT
• Current Price:      ${current_price:,.4f}

1. ENTRY ROADMAP (100 USDT ALLOCATION):
{entry_style_text}

2. STOP LOSS & MAXIMUM RISK:
• Hard Stop Loss:     ${stop_loss:,.4f} (-{risk_pct:.2f}%)
• Maximum Dollar Risk: -${max_loss_usdt:.2f} USDT

3. TAKE PROFIT TARGETS:
• TP1 (Sell 50% Position): ${tp1:,.4f} (+{tp1_gain_pct:.2f}%) -> Locks ~$52.00 USDT back to Cash
• TP2 (Sell Remaining 50%): ${tp2:,.4f} (+{tp2_gain_pct:.2f}%) -> Captures full trend expansion

4. BREAK-EVEN & TRAILING STOP INSTRUCTIONS:
• As soon as TP1 (${tp1:,.4f}) is reached:
  -> IMMEDIATELY move your Stop Loss on remaining coins to ${be_price:,.4f} (Entry + Fees).
  -> This guarantees a 100% Risk-Free / Profitable trade!
• If price continues higher, trail Stop Loss below 1H SuperTrend.

5. DETECTION REASON & MARKET STATE:
• Trigger Reason: {reason}
• Safety Status:  {safety_info.get('timing_msg', 'Normal') if safety_info else 'Normal'}
================================================================================
"""

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 20px; }}
    .card {{ background: #ffffff; border-radius: 12px; max-width: 650px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.08); overflow: hidden; border: 1px solid #e2e8f0; }}
    .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%); color: #ffffff; padding: 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
    .header p {{ margin: 6px 0 0 0; font-size: 14px; opacity: 0.9; color: #38bdf8; }}
    .time-badge {{ background: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 20px; font-size: 12px; display: inline-block; margin-top: 8px; }}
    .tf-badge {{ background: #38bdf8; color: #0f172a; padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 13px; display: inline-block; margin-left: 6px; }}
    .content {{ padding: 24px; }}
    .section {{ margin-bottom: 22px; border-bottom: 1px solid #e2e8f0; padding-bottom: 18px; }}
    .section:last-child {{ border-bottom: none; }}
    .section-title {{ font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 10px; }}
    .metric-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .metric-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }}
    .metric-label {{ font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase; }}
    .metric-value {{ font-size: 16px; font-weight: 700; color: #0f172a; margin-top: 4px; }}
    .danger {{ color: #dc2626; }}
    .warning-box {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; border-radius: 6px; font-size: 13px; color: #92400e; margin-top: 10px; }}
    .plan-box {{ background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 14px; margin-top: 10px; font-size: 14px; }}
    .footer {{ background: #f1f5f9; text-align: center; padding: 16px; font-size: 12px; color: #64748b; }}
</style>
</head>
<body>
<div class="card">
    <div class="header">
        <h1>🟢 BINANCE SPOT BUY SIGNAL</h1>
        <p>{symbol} • Strategy: {strategy} • 100 USDT Capital</p>
        <div class="time-badge">🕒 Signal Time: <b>{signal_time_str}</b></div>
    </div>
    <div class="content">
        <!-- TradingView Timeframe Highlight -->
        <div class="section" style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:14px;">
            <div style="font-size:13px; color:#166534; font-weight:700; text-transform:uppercase;">📈 TradingView Chart Timeframe</div>
            <div style="font-size:18px; font-weight:800; color:#15803d; margin-top:4px;">
                Open Chart on: <span style="background:#dcfce7; border:1px solid #86efac; padding:2px 10px; border-radius:6px;">{timeframe}</span>
            </div>
            <div style="font-size:12px; color:#166534; margin-top:4px;">Is trade ka zone aur candle formation dekhne ke liye TradingView par <b>{timeframe}</b> timeframe use karein.</div>
        </div>

        <!-- Timestamps Overview -->
        <div class="section">
            <div class="section-title">⏱️ Exact Timestamps (PKT & UTC)</div>
            <div class="metric-box" style="margin-bottom:8px;">
                <div class="metric-label">Signal Generated At</div>
                <div class="metric-value" style="font-size:14px; color:#0284c7;">{signal_time_str}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Zone / Candle Formed At ({timeframe})</div>
                <div class="metric-value" style="font-size:14px; color:#475569;">{candle_time_str}</div>
            </div>
        </div>

        <!-- Trade Overview -->
        <div class="section">
            <div class="section-title">📊 Trade Overview</div>
            <div class="metric-grid">
                <div class="metric-box">
                    <div class="metric-label">Pair / Symbol</div>
                    <div class="metric-value">{symbol}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Current Market Price</div>
                    <div class="metric-value">${current_price:,.4f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Allocated Capital</div>
                    <div class="metric-value">$100.00 USDT</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Max Risk Amount</div>
                    <div class="metric-value danger">-${max_loss_usdt:.2f} USDT (-{risk_pct:.2f}%)</div>
                </div>
            </div>
        </div>

        <!-- Entry Plan -->
        <div class="section">
            <div class="section-title">🛒 Step 1: 100 USDT Entry Plan</div>
            {entry_style_html}
        </div>

        <!-- SL & TP -->
        <div class="section">
            <div class="section-title">🛑 Step 2: Stop Loss & Profit Targets</div>
            <table style="width:100%; border-collapse: collapse; margin-top: 8px; font-size:14px;">
                <tr style="background:#fee2e2;">
                    <td style="padding:10px; border:1px solid #fca5a5; font-weight:700; color:#991b1b;">Stop Loss (Hard Stop)</td>
                    <td style="padding:10px; border:1px solid #fca5a5; font-weight:700; color:#991b1b;">${stop_loss:,.4f}</td>
                    <td style="padding:10px; border:1px solid #fca5a5; color:#991b1b;">-{risk_pct:.2f}% (-${max_loss_usdt:.2f} USDT)</td>
                </tr>
                <tr style="background:#dcfce7;">
                    <td style="padding:10px; border:1px solid #86efac; font-weight:700; color:#166534;">Take Profit 1 (Sell 50%)</td>
                    <td style="padding:10px; border:1px solid #86efac; font-weight:700; color:#166534;">${tp1:,.4f}</td>
                    <td style="padding:10px; border:1px solid #86efac; color:#166534;">+{tp1_gain_pct:.2f}% (Lock ~$52.00 USDT)</td>
                </tr>
                <tr style="background:#dcfce7;">
                    <td style="padding:10px; border:1px solid #86efac; font-weight:700; color:#166534;">Take Profit 2 (Sell 50%)</td>
                    <td style="padding:10px; border:1px solid #86efac; font-weight:700; color:#166534;">${tp2:,.4f}</td>
                    <td style="padding:10px; border:1px solid #86efac; color:#166534;">+{tp2_gain_pct:.2f}% (Trend Expansion)</td>
                </tr>
            </table>
        </div>

        <!-- Trade Management & Trailing SL -->
        <div class="section">
            <div class="section-title">🔄 Step 3: Break-Even & Trade Management Rules</div>
            <div class="plan-box">
                <b>1. Breakeven Shift Rule:</b> Jaise hi price <b>${tp1:,.4f} (TP1)</b> hit kare aur aap 50% sell kar dein, apne baqi bache hue coins ka Stop Loss foran barha kar <b>${be_price:,.4f}</b> (Breakeven + Fees) par shift kar dein.<br><br>
                <b>2. Zero-Loss Guarantee:</b> Iske baad ye trade 100% risk-free ho jayegi.<br><br>
                <b>3. Trailing Rule:</b> Price mazid ooper jaye to SL ko 1H SuperTrend line ke sath-sath trail karte jayein.
            </div>
        </div>

        <!-- Safety & Reason -->
        <div class="section">
            <div class="section-title">🛡️ Detection Reason & Market Safety</div>
            <p style="font-size:13px; color:#334155; margin:0 0 6px 0;"><b>Algorithm Trigger:</b> {reason}</p>
            <div class="warning-box">
                <b>Market Safety Note:</b> {safety_info.get('timing_msg', 'Normal') if safety_info else 'Normal trading conditions verified.'}
            </div>
        </div>
    </div>
    <div class="footer">
        Binance Spot Autonomous Quantitative Scanner • Phase 1 Live Validation
    </div>
</div>
</body>
</html>
"""
        return self.send_email(subject, html_content, text_content)

    def send_12h_summary_email(self, period_start_utc: Any, period_end_utc: Any,
                               total_qualified: int, win_count: int, loss_count: int,
                               unresolved_count: int, net_pnl_usdt: float,
                               trades_details: List[Dict[str, Any]],
                               open_positions_details: List[Dict[str, Any]]) -> bool:
        """
        Dispatches the 12-Hour Trading Activity Summary Email with dual PKT + UTC timestamps.
        """
        start_str = format_dual_time(period_start_utc)
        end_str = format_dual_time(period_end_utc)
        
        subject = f"📊 [12-HOUR SUMMARY] Binance Spot Activity Report | {format_dual_time()}"
        
        # Build Table of Closed Trades
        trade_rows_html = []
        trade_rows_text = []
        
        for t in trades_details:
            entry_time_str = format_dual_time(t.get("entry_time"))
            exit_time_str = format_dual_time(t.get("exit_time"))
            pnl_val = t.get("net_pnl_usdt", 0.0)
            pnl_pct = t.get("net_pnl_pct", 0.0)
            status = "🟢 WIN" if pnl_val > 0 else "🔴 LOSS"
            
            tf_val = t.get("timeframe", "15m" if "S3" in t.get("strategy", "") else "1h")
            trade_rows_text.append(
                f"• {status} | {t.get('symbol')} ({t.get('strategy')}) [TF: {tf_val}]\n"
                f"  Entry: ${t.get('entry_price', 0):,.4f} at {entry_time_str}\n"
                f"  Exit:  ${t.get('exit_price', 0):,.4f} at {exit_time_str}\n"
                f"  PnL:   ${pnl_val:+,.2f} ({pnl_pct:+.2f}%) | Reason: {t.get('exit_reason')}\n"
            )
            
            row_bg = "#dcfce7" if pnl_val > 0 else "#fee2e2"
            pnl_color = "#166534" if pnl_val > 0 else "#991b1b"
            
            trade_rows_html.append(f"""
            <tr style="background:{row_bg};">
                <td style="padding:8px; border:1px solid #cbd5e1; font-weight:700;">{t.get('symbol')}</td>
                <td style="padding:8px; border:1px solid #cbd5e1; font-size:12px;">{t.get('strategy')}</td>
                <td style="padding:8px; border:1px solid #cbd5e1; font-weight:700; color:#0284c7;">{tf_val}</td>
                <td style="padding:8px; border:1px solid #cbd5e1;">${t.get('entry_price', 0):,.4f}<br><small style="color:#64748b;">{entry_time_str}</small></td>
                <td style="padding:8px; border:1px solid #cbd5e1;">${t.get('exit_price', 0):,.4f}<br><small style="color:#64748b;">{exit_time_str}</small></td>
                <td style="padding:8px; border:1px solid #cbd5e1; font-weight:700; color:{pnl_color};">${pnl_val:+,.2f} ({pnl_pct:+.2f}%)</td>
                <td style="padding:8px; border:1px solid #cbd5e1; font-size:12px;">{t.get('exit_reason')}</td>
            </tr>
            """)

        # Build Table of Unresolved / Active Trades
        unresolved_rows_html = []
        unresolved_rows_text = []
        
        for pos in open_positions_details:
            entry_time_str = format_dual_time(pos.get("entry_time"))
            curr_p = pos.get("current_price", pos.get("entry_price", 0))
            entry_p = pos.get("entry_price", 1)
            unrealized_pct = ((curr_p - entry_p) / entry_p) * 100.0
            pos_tf = pos.get("timeframe", "15m" if "S3" in pos.get("strategy", "") else "1h")
            
            unresolved_rows_text.append(
                f"• 🟡 ACTIVE | {pos.get('symbol')} ({pos.get('strategy')}) [TF: {pos_tf}]\n"
                f"  Entry: ${entry_p:,.4f} at {entry_time_str}\n"
                f"  Current Price: ${curr_p:,.4f} | Unrealized: {unrealized_pct:+.2f}%\n"
                f"  Stop Loss: ${pos.get('stop_loss', 0):,.4f} | TP1: ${pos.get('tp1', 0):,.4f}\n"
            )
            
            unresolved_rows_html.append(f"""
            <tr style="background:#fef9c3;">
                <td style="padding:8px; border:1px solid #cbd5e1; font-weight:700;">{pos.get('symbol')}</td>
                <td style="padding:8px; border:1px solid #cbd5e1; font-size:12px;">{pos.get('strategy')}</td>
                <td style="padding:8px; border:1px solid #cbd5e1; font-weight:700; color:#0284c7;">{pos_tf}</td>
                <td style="padding:8px; border:1px solid #cbd5e1;">${entry_p:,.4f}<br><small style="color:#64748b;">{entry_time_str}</small></td>
                <td style="padding:8px; border:1px solid #cbd5e1;">${curr_p:,.4f}</td>
                <td style="padding:8px; border:1px solid #cbd5e1; font-weight:700; color:{'#166534' if unrealized_pct >= 0 else '#991b1b'};">{unrealized_pct:+.2f}%</td>
                <td style="padding:8px; border:1px solid #cbd5e1; font-size:12px;">SL: ${pos.get('stop_loss', 0):,.4f}<br>TP1: ${pos.get('tp1', 0):,.4f}</td>
            </tr>
            """)

        closed_table_html = "".join(trade_rows_html) if trade_rows_html else "<tr><td colspan='7' style='padding:12px; text-align:center; color:#64748b;'>No closed trades in this 12-hour window.</td></tr>"
        unresolved_table_html = "".join(unresolved_rows_html) if unresolved_rows_html else "<tr><td colspan='7' style='padding:12px; text-align:center; color:#64748b;'>No unresolved / active trades currently open.</td></tr>"

        text_content = f"""
================================================================================
12-HOUR BINANCE SPOT TRADING ACTIVITY REPORT
================================================================================
Window: {start_str}  -->  {end_str}

EXECUTIVE SUMMARY:
• Total Qualified Trades: {total_qualified}
• Realized Wins:         {win_count}
• Realized Losses:       {loss_count}
• Unresolved / Active:   {unresolved_count}
• Net Realized PnL:      ${net_pnl_usdt:+,.2f} USDT

--------------------------------------------------------------------------------
1. REALIZED CLOSED TRADES:
{chr(10).join(trade_rows_text) if trade_rows_text else 'None'}

--------------------------------------------------------------------------------
2. UNRESOLVED / ACTIVE POSITIONS:
{chr(10).join(unresolved_rows_text) if unresolved_rows_text else 'None'}
================================================================================
"""

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 20px; }}
    .card {{ background: #ffffff; border-radius: 12px; max-width: 750px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.08); overflow: hidden; border: 1px solid #e2e8f0; }}
    .header {{ background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); color: #ffffff; padding: 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
    .header p {{ margin: 6px 0 0 0; font-size: 13px; color: #c7d2fe; }}
    .content {{ padding: 24px; }}
    .section {{ margin-bottom: 24px; }}
    .section-title {{ font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 12px; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }}
    .metric-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; text-align: center; }}
    .metric-label {{ font-size: 11px; color: #64748b; font-weight: 600; text-transform: uppercase; }}
    .metric-value {{ font-size: 18px; font-weight: 700; color: #0f172a; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }}
    th {{ background: #f1f5f9; padding: 8px; border: 1px solid #cbd5e1; text-align: left; }}
    .footer {{ background: #f1f5f9; text-align: center; padding: 16px; font-size: 12px; color: #64748b; }}
</style>
</head>
<body>
<div class="card">
    <div class="header">
        <h1>📊 12-HOUR TRADING ACTIVITY SUMMARY</h1>
        <p>Period: <b>{start_str}</b> &nbsp;➔&nbsp; <b>{end_str}</b></p>
    </div>
    <div class="content">
        <!-- 12h Metrics -->
        <div class="section">
            <div class="section-title">📈 12-Hour Performance Scorecard</div>
            <div class="metric-grid">
                <div class="metric-box">
                    <div class="metric-label">Total Qualified</div>
                    <div class="metric-value">{total_qualified}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Wins</div>
                    <div class="metric-value" style="color:#16a34a;">{win_count}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Losses</div>
                    <div class="metric-value" style="color:#dc2626;">{loss_count}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Active / Unresolved</div>
                    <div class="metric-value" style="color:#d97706;">{unresolved_count}</div>
                </div>
            </div>
        </div>

        <!-- Realized Closed Trades -->
        <div class="section">
            <div class="section-title">✅ Realized Closed Trades in Last 12h ({len(trades_details)})</div>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Strategy</th>
                    <th>TradingView TF</th>
                    <th>Entry Price & Time</th>
                    <th>Exit Price & Time</th>
                    <th>Net PnL</th>
                    <th>Exit Reason</th>
                </tr>
                {closed_table_html}
            </table>
        </div>

        <!-- Unresolved / Active Positions -->
        <div class="section">
            <div class="section-title">🟡 Unresolved / Still Active Positions ({len(open_positions_details)})</div>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Strategy</th>
                    <th>TradingView TF</th>
                    <th>Entry Price & Time</th>
                    <th>Current Price</th>
                    <th>Unrealized PnL</th>
                    <th>Targets (SL / TP1)</th>
                </tr>
                {unresolved_table_html}
            </table>
        </div>
    </div>
    <div class="footer">
        Binance Spot Autonomous Quantitative Scanner • 12-Hour Scheduled Summary
    </div>
</div>
</body>
</html>
"""
    def send_btc_emergency_dump_alert(self, btc_drop_pct: float,
                                       active_positions: List[Dict[str, Any]],
                                       btc_price: float) -> bool:
        """
        P6: Dispatches an urgent, high-priority alert when BTC drops >= 1.2% in 15 minutes
        while positions are active. Explicitly advises the user to move Stop Loss to Entry Price.
        """
        dual_time = format_dual_time()
        pos_count = len(active_positions)
        symbols_str = ", ".join([p.get("symbol", "") for p in active_positions])

        subject = f"🚨 URGENT ACTION: BTC Flash Dump ({btc_drop_pct:.2f}%) — Move SL to Entry Price for {symbols_str}"

        # Plain text
        text_content = f"""🚨 URGENT CAPITAL PROTECTION ALERT
Time: {dual_time}

Yaar, aapki {pos_count} trade(s) [{symbols_str}] is waqt open/active hain aur Bitcoin ne pichle 15 minutes mein {btc_drop_pct:.2f}% dump kiya hai (BTC: ${btc_price:,.2f}).

Is wajah se apni active trade ka Stop Loss Entry Price par shift kar dein, taake trade ka capital protect ho sake!

Active Trade Details:
"""
        for p in active_positions:
            sym = p.get("symbol", "")
            strat = p.get("strategy", "")
            ep = p.get("entry_price", 0)
            be_sl = ep * 1.001
            text_content += f"- {sym} ({strat}): Entry ${ep:,.4f} -> Recommended New SL: ${be_sl:,.4f}\n"

        # HTML Table of positions
        pos_rows_html = ""
        for p in active_positions:
            sym = p.get("symbol", "")
            strat = p.get("strategy", "")
            ep = p.get("entry_price", 0)
            curr = p.get("current_price", ep)
            old_sl = p.get("old_sl", p.get("stop_loss", 0))
            be_sl = ep * 1.001
            pos_rows_html += f"""
            <tr>
                <td style="padding:10px; font-weight:bold; color:#1e293b;">{sym}</td>
                <td style="padding:10px; font-size:12px; color:#64748b;">{strat}</td>
                <td style="padding:10px; font-weight:bold;">${ep:,.4f}</td>
                <td style="padding:10px; color:#475569;">${curr:,.4f}</td>
                <td style="padding:10px; color:#dc2626; text-decoration:line-through;">${old_sl:,.4f}</td>
                <td style="padding:10px; font-weight:bold; color:#16a34a; background:#f0fdf4;">${be_sl:,.4f} (Entry + Fee)</td>
            </tr>
            """

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }}
    .container {{ max-width: 650px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 2px solid #ef4444; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.15); }}
    .header {{ background: linear-gradient(135deg, #dc2626, #b91c1c); color: #ffffff; padding: 25px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 24px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; }}
    .header p {{ margin: 8px 0 0 0; opacity: 0.95; font-size: 14px; }}
    .content {{ padding: 25px; color: #334155; }}
    .urgent-banner {{ background: #fef2f2; border-left: 5px solid #ef4444; padding: 15px; border-radius: 6px; margin-bottom: 20px; }}
    .urgent-banner p {{ margin: 0; font-size: 15px; line-height: 1.5; color: #991b1b; font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
    th {{ background: #f1f5f9; padding: 10px; text-align: left; color: #475569; font-weight: 700; border-bottom: 2px solid #cbd5e1; }}
    tr:nth-child(even) {{ background: #f8fafc; }}
    .footer {{ background: #f1f5f9; padding: 15px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🚨 URGENT CAPITAL PROTECTION ALERT</h1>
        <p>BTC Flash Dump Triggered • Action Required</p>
    </div>
    <div class="content">
        <div class="urgent-banner">
            <p>
                ⚠️ <b>Yaar, aapki {pos_count} trade(s) is waqt open/active hain aur Bitcoin ne pichle 15 minutes mein {btc_drop_pct:.2f}% dump kiya hai (BTC: ${btc_price:,.2f}).</b>
                <br><br>
                Is wajah se apni active trade ka Stop Loss <b>Entry Price par shift kar dein</b>, taake market cascade mein trade ka capital 100% protect ho sake!
            </p>
        </div>

        <h3 style="margin: 20px 0 10px 0; color: #1e293b; font-size: 16px;">Active Positions SL Adjustment Guide</h3>
        <table>
            <tr>
                <th>Symbol</th>
                <th>Strategy</th>
                <th>Entry Price</th>
                <th>Current Price</th>
                <th>Old Stop Loss</th>
                <th>Recommended New SL</th>
            </tr>
            {pos_rows_html}
        </table>

        <div style="margin-top: 20px; padding: 12px; background: #f0fdf4; border-radius: 6px; border: 1px solid #bbf7d0; font-size: 13px; color: #166534;">
            ✅ <b>Automatic Paper Defense:</b> Scanner broker ne paper account mein Stop Loss ko Breakeven par shift kar diya hai. Agar aap live exchange par trade kar rahe hain to wahan bhi foran SL shift kar dein.
        </div>
    </div>
    <div class="footer">
        Timestamp: {dual_time} • Binance Spot Risk Management Protocol
    </div>
</div>
</body>
</html>
"""
        return self.send_email(subject, html_content, text_content)
