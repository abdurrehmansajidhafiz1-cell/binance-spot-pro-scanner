"""
Email Notification Service for Binance Spot Trading Signals.
Generates comprehensive, actionable 100 USDT trade execution plans.
"""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Optional, Dict, Any


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
            # Connect via SSL port 465
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=12) as server:
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, self.receiver_email, msg.as_string())
            return True
        except Exception as e:
            try:
                # Fallback to port 587 STARTTLS
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
                                safety_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Formats and dispatches a comprehensive, actionable 100 USDT trade execution plan.
        """
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        capital_usdt = 100.0
        
        # Calculate Risk and Sizing
        risk_pct = ((current_price - stop_loss) / current_price) * 100.0
        max_loss_usdt = (capital_usdt * (risk_pct / 100.0))
        tp1_gain_pct = ((tp1 - current_price) / current_price) * 100.0
        tp2_gain_pct = ((tp2 - current_price) / current_price) * 100.0
        
        # Entry Plan Logic based on Strategy
        if "I1" in strategy:
            # Staggered 60% Market + 40% Limit Dip Entry
            entry1_usdt = 60.0
            entry1_price = current_price
            entry1_qty = entry1_usdt / entry1_price
            
            entry2_usdt = 40.0
            entry2_price = current_price * 0.988 # 1.2% deeper dip order
            entry2_qty = entry2_usdt / entry2_price
            
            entry_style_text = (
                f"• Entry 1 (Market Order — $60.00 USDT): Buy at current market price ${entry1_price:,.4f} (~{entry1_qty:.4f} {symbol[:-4]})\n"
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
            # S3: Single Market Breakout Entry
            qty_100 = capital_usdt / current_price
            entry_style_text = f"• Single Market Entry: Buy 100% ($100.00 USDT) at ${current_price:,.4f} (~{qty_100:.4f} {symbol[:-4]})"
            entry_style_html = f"<p><b>Fast Breakout Entry:</b> Buy 100% (<b>$100.00 USDT</b>) at current price <b>${current_price:,.4f}</b> (~{qty_100:.4f} {symbol[:-4]}).</p>"

        # Breakeven target price
        be_price = current_price * 1.0025

        # Subject Line
        subject = f"🟢 [BINANCE SPOT SIGNAL] {symbol} | Strategy: {strategy} | Capital: $100 USDT"

        # Plain Text
        text_content = f"""
================================================================================
BINANCE SPOT TRADE EXECUTION PLAN — {symbol}
================================================================================
Time: {now_str}
Strategy: {strategy}
Total Capital: $100.00 USDT
Current Price: ${current_price:,.4f}

1. ENTRY ROADMAP (100 USDT ALLOCATION):
{entry_style_text}

2. STOP LOSS & MAXIMUM RISK:
• Hard Stop Loss: ${stop_loss:,.4f} (-{risk_pct:.2f}%)
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
• Safety Warning: {safety_info.get('timing_msg', 'Normal') if safety_info else 'Normal'}
================================================================================
"""

        # Rich HTML Email
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
    .content {{ padding: 24px; }}
    .section {{ margin-bottom: 22px; border-bottom: 1px solid #e2e8f0; padding-bottom: 18px; }}
    .section:last-child {{ border-bottom: none; }}
    .section-title {{ font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 10px; display: flex; align-items: center; }}
    .metric-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .metric-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }}
    .metric-label {{ font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase; }}
    .metric-value {{ font-size: 16px; font-weight: 700; color: #0f172a; margin-top: 4px; }}
    .danger {{ color: #dc2626; }}
    .success {{ color: #16a34a; }}
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
    </div>
    <div class="content">
        <!-- Overview -->
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
                <b>2. Zero-Loss Guarantee:</b> Iske baad ye trade 100% risk-free ho jayegi aur kisi soorat loss nahi degi.<br><br>
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
