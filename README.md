# 🚀 Binance Spot Autonomous Quantitative Scanner (Phase 1)

Professional, purely Spot-compatible, automated crypto trading scanner and paper trading execution engine. Designed to run **100% autonomously on GitHub Actions** triggered via **External Cron Job (cron-job.org)** across the **Top 50 Liquid Binance Spot pairs**.

---

## 🧠 Phase 1 Strategies Included

1. **Strategy I1: Multi-Timeframe Trend + Volatility Pullback ($4\text{H} + 1\text{H}$)**
   - Macro Trend ($4\text{H}$): $EMA_{200}$ Filter + SuperTrend ($10, 3.0$) Bullish Alignment.
   - Execution ($1\text{H}$): Retracement into $EMA_{21}$ dynamic support with RSI ($38 - 55$) reset.
   - Entry Plan: Staggered 60% Market Buy + 40% Limit Dip Order.
   - Target: $1.5R$ TP1 (50% sell & breakeven shift) and $3.0R$ TP2.

2. **Strategy I2: Cross-Sectional Momentum & Relative Strength ($1\text{D} + 4\text{H}$)**
   - Macro Regime ($1\text{D}$): BTC $> 50\text{-day SMA}$. If False $\implies$ 100% Cash (USDT) preservation.
   - Decile Ranking: Ranks 50 coins by 14-day Risk-Adjusted Momentum ($\text{Return}_{14\text{d}} / \text{Vol}_{30\text{d}}$) and selects the Top 5 market leaders ($20 USDT allocation each).

3. **Strategy S3: Volatility Squeeze Breakout ($15\text{m}$)**
   - Bollinger Bands ($20, 2.0$) contracting inside Keltner Channels ($20, 1.5 ATR$).
   - Squeeze fire expansion + OBV above 20 EMA + positive momentum.
   - Target: $+1.0\%$ TP1 (locks fees/profit) and $+2.0 \times ATR$ TP2.

---

## 🛡️ Global Market Safety Shield
- **Sunday/Monday CME Open Filter:** Flags high-manipulation weekend gap hours (Sunday 20:00 UTC to Monday 08:00 UTC).
- **BTC Flash-Dump Circuit Breaker:** Suppresses altcoin longs if BTC drops $> 1.5\%$ in 45 minutes.
- **Altcoin Cascade Filter:** Blocks new signals if $> 70\%$ of universe is dumping simultaneously.

---

## 📩 Actionable 100 USDT Email Notifications
Every signal triggers an email to `abdurrehmansajidhafiz1@gmail.com` with:
- Exact 100 USDT order sizing and split plan.
- Stop Loss level and exact dollar risk amount.
- Take Profit 1 & Take Profit 2 targets.
- Exact Breakeven and Trailing Stop rules.

---

## ⏰ External Cron Job (cron-job.org) Setup Guide

To ensure GitHub runs every 15 minutes without missing a schedule:

1. Create a free account on **[cron-job.org](https://cron-job.org)**.
2. Click **Create Cronjob**.
3. **Title:** `Binance Spot 15m Scanner`
4. **URL:**
   ```
   https://api.github.com/repos/abdurrehmansajidhafiz1-cell/binance-spot-pro-scanner/dispatches
   ```
5. **Execution Schedule:** Every 15 minutes (`*/15 * * * *`).
6. **Request Method:** `POST`
7. **HTTP Headers:**
   - Header 1: `Accept: application/vnd.github.v3+json`
   - Header 2: `Authorization: Bearer YOUR_GITHUB_PAT_TOKEN`
   - Header 3: `User-Agent: CronJob-Dispatcher`
8. **Request Body (JSON):**
   ```json
   {"event_type": "cron_trigger"}
   ```
9. Click **Create / Save**.

---

## 📊 Live Dashboard & Tracking

All simulated paper trades and live statistics are logged in:
👉 **[LIVE_RESULTS.md](LIVE_RESULTS.md)**
