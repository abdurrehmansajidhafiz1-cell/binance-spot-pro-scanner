# 🚀 Binance Spot 15-Day Live Paper Trading Dashboard

[![Portfolio Return](https://img.shields.io/badge/Net_Return--3.75%25-red?style=for-the-badge)](LIVE_RESULTS.md)
[![Win Rate](https://img.shields.io/badge/Win_Rate-25.0%25-blue?style=for-the-badge)](LIVE_RESULTS.md)
[![Profit Factor](https://img.shields.io/badge/Profit_Factor-0.21-orange?style=for-the-badge)](LIVE_RESULTS.md)
[![Total Qualified Trades](https://img.shields.io/badge/Total_Qualified-20-informational?style=for-the-badge)](LIVE_RESULTS.md)

> **Last Updated:** `2026-09-08 19:16:06 PKT (14:16:06 UTC)`  
> **Testing Start Date:** `2026-09-07 17:00:00 PKT (12:00:00 UTC)`  
> **Target Universe:** Top 50 Liquid Binance Spot Pairs (Zero Futures / Pure Spot)
> **Fixed Trade Budget:** `$100 USDT per trade` | **PKR Rate:** `₨278 per $1 USD`

---

## 📊 Executive Performance Summary (Unique Trades)

| Metric | Value | Metric | Value |
| :--- | :--- | :--- | :--- |
| **Starting Balance** | `$500.00 USDT` | **Total Qualified Trades** | `20 Unique Trades` |
| **Current Equity** | `$481.23 USDT` | **Completed Trades** | `20 Trades` |
| **Available Cash** | `$481.23 USDT` | **Active / In-Trade** | `0 Trade` |
| **Net PnL ($)** | `-$18.77 USDT` | **Win / Loss Ratio** | `5 Win / 15 Loss` |
| **Net Return (%)** | `-3.75%` | **Win Rate** | `25.00%` |
| **Peak Equity** | `$500.00 USDT` | **Profit Factor** | `0.21` |
| **Max Drawdown** | `-3.75%` | **Total Fees Deducted** | `$2.99 USDT` |

---

## 🟡 Active Open Positions (0)

> **🛡️ Rule 1 (Break-Even Capital Defense Protocol):**
> - **I1 Strategy:** Jab trade +1.50% gain reach karti hai, toh Stop Loss automatically Entry Price (+0.15% fee buffer) par lock ho jata hai. Trade bina TP1 hit hue bhi **100% Risk-Free (Safe)** ho jati hai.
> - **S3 Strategy:** Jab TP1 hit hota hai, toh 50% profit lock hone ke sath baqi position ka Stop Loss Breakeven par shift ho jata hai.
> - **Milestone Indicators:** `🟢 HIT (🛡️ Safe / SL Locked)` = Trade risk-free ho chuki hai | `⚪ Pending` = Break-even target ka intezar hai.

_No active open positions currently._

---

## 📜 Completed Trades Postmortem History (20)

> **Result Badges Guide:**
> - `🟢 FULL WIN` → TP2 reached (100% profit target captured)
> - `🟢 PARTIAL WIN` → TP1 reached, remainder closed at Breakeven SL
> - `🛡️ BREAKEVEN PROTECTED` → Early Break-Even hit (+1.50%), trade closed at Entry/Fees with capital 100% safe (Zero Loss)
> - `🔴 LOSS` → Hard Stop Loss hit before reaching Break-Even
>
> **PKR Column Guide:**
> - 💵 `$100 Trade` → Actual realized profit/fees in PKR (actual budget used)
> - 📌 `$35 Ref` → Reference-only: what the same trade would have earned with $35 budget (no actual trades at $35)
> - PKR Rate used: **₨278 per $1 USD**

| Symbol   | Strategy              | TradingView Timeframe   | Zone Formed (PKT/UTC)                  | Signal Time (PKT/UTC)                  | Entry Price & Time                                                 | TP1 Price & Hit Time                                             | TP2 Price & Hit Time                                             | SL Hit Time                            | Net PnL ($ / %)   | PKR Calculations (Rate: ₨278/$)                                                                           | Final Result           |
|----------|-----------------------|-------------------------|----------------------------------------|----------------------------------------|--------------------------------------------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|----------------------------------------|-------------------|-----------------------------------------------------------------------------------------------------------|------------------------|
| DOTUSDT  | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-08 14:45:00 PKT (09:45:00 UTC) | 2026-09-08 15:01:06 PKT (10:01:06 UTC) | $1.0875<br><small>2026-09-08 15:01:06 PKT (10:01:06 UTC)</small>   | $1.1000<br><small>-</small>                                      | $1.1087<br><small>-</small>                                      | 2026-09-08 16:00:45 PKT (11:00:45 UTC) | -0.03 (-0.03%)    | 💵 **$100 Trade:** `-7 PKR` profit | Fees: `42 PKR`<br>📌 **$35 Ref:** `-2 PKR` profit | Fees: `15 PKR`     | 🛡️ BREAKEVEN PROTECTED |
| UNIUSDT  | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-08 14:30:00 PKT (09:30:00 UTC) | 2026-09-08 14:46:03 PKT (09:46:03 UTC) | $7.1846<br><small>2026-09-08 14:46:03 PKT (09:46:03 UTC)</small>   | $7.2490<br><small>-</small>                                      | $7.3063<br><small>-</small>                                      | 2026-09-08 15:45:29 PKT (10:45:29 UTC) | -2.44 (-2.44%)    | 💵 **$100 Trade:** `-679 PKR` profit | Fees: `41 PKR`<br>📌 **$35 Ref:** `-238 PKR` profit | Fees: `14 PKR` | 🔴 LOSS                 |
| AVAXUSDT | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-08 14:30:00 PKT (09:30:00 UTC) | 2026-09-08 14:45:54 PKT (09:45:54 UTC) | $8.1121<br><small>2026-09-08 14:45:54 PKT (09:45:54 UTC)</small>   | $8.2043<br><small>-</small>                                      | $8.2691<br><small>-</small>                                      | 2026-09-08 15:30:39 PKT (10:30:39 UTC) | -0.03 (-0.03%)    | 💵 **$100 Trade:** `-7 PKR` profit | Fees: `42 PKR`<br>📌 **$35 Ref:** `-2 PKR` profit | Fees: `15 PKR`     | 🛡️ BREAKEVEN PROTECTED |
| ICPUSDT  | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-08 13:30:00 PKT (08:30:00 UTC) | 2026-09-08 13:46:07 PKT (08:46:07 UTC) | $3.0695<br><small>2026-09-08 13:46:07 PKT (08:46:07 UTC)</small>   | $3.1099<br><small>-</small>                                      | $3.1345<br><small>-</small>                                      | 2026-09-08 15:30:39 PKT (10:30:39 UTC) | -0.03 (-0.03%)    | 💵 **$100 Trade:** `-7 PKR` profit | Fees: `42 PKR`<br>📌 **$35 Ref:** `-2 PKR` profit | Fees: `15 PKR`     | 🛡️ BREAKEVEN PROTECTED |
| APTUSDT  | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-08 14:15:00 PKT (09:15:00 UTC) | 2026-09-08 14:31:07 PKT (09:31:07 UTC) | $0.6463<br><small>2026-09-08 14:31:07 PKT (09:31:07 UTC)</small>   | $0.6548<br><small>2026-09-08 14:45:29 PKT (09:45:29 UTC)</small> | $0.6599<br><small>2026-09-08 15:00:40 PKT (10:00:40 UTC)</small> | -                                      | +1.58 (+1.58%)    | 💵 **$100 Trade:** `+439 PKR` profit | Fees: `42 PKR`<br>📌 **$35 Ref:** `+154 PKR` profit | Fees: `15 PKR` | 🟢 FULL WIN             |
| KAVAUSDT | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-08 08:45:00 PKT (03:45:00 UTC) | 2026-09-08 09:01:35 PKT (04:01:35 UTC) | $0.0602<br><small>2026-09-08 09:01:35 PKT (04:01:35 UTC)</small>   | $0.0608<br><small>-</small>                                      | $0.0613<br><small>-</small>                                      | 2026-09-08 10:45:29 PKT (05:45:29 UTC) | -2.47 (-2.47%)    | 💵 **$100 Trade:** `-687 PKR` profit | Fees: `41 PKR`<br>📌 **$35 Ref:** `-240 PKR` profit | Fees: `14 PKR` | 🔴 LOSS                 |
| NEARUSDT | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-08 05:45:00 PKT (00:45:00 UTC) | 2026-09-08 06:01:07 PKT (01:01:07 UTC) | $2.3682<br><small>2026-09-08 06:01:07 PKT (01:01:07 UTC)</small>   | $2.3954<br><small>-</small>                                      | $2.4143<br><small>-</small>                                      | 2026-09-08 08:00:44 PKT (03:00:44 UTC) | -2.67 (-2.67%)    | 💵 **$100 Trade:** `-743 PKR` profit | Fees: `41 PKR`<br>📌 **$35 Ref:** `-260 PKR` profit | Fees: `14 PKR` | 🔴 LOSS                 |
| EGLDUSDT | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-08 05:00:00 PKT (00:00:00 UTC) | 2026-09-08 05:16:11 PKT (00:16:11 UTC) | $4.7304<br><small>2026-09-08 05:16:11 PKT (00:16:11 UTC)</small>   | $4.7868<br><small>-</small>                                      | $4.8246<br><small>-</small>                                      | 2026-09-08 08:00:44 PKT (03:00:44 UTC) | -1.70 (-1.70%)    | 💵 **$100 Trade:** `-472 PKR` profit | Fees: `41 PKR`<br>📌 **$35 Ref:** `-165 PKR` profit | Fees: `14 PKR` | 🔴 LOSS                 |
| DOGEUSDT | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-08 05:00:00 PKT (00:00:00 UTC) | 2026-09-08 05:15:50 PKT (00:15:50 UTC) | $0.0910<br><small>2026-09-08 05:15:50 PKT (00:15:50 UTC)</small>   | $0.0922<br><small>-</small>                                      | $0.0929<br><small>-</small>                                      | 2026-09-08 08:00:43 PKT (03:00:43 UTC) | -1.06 (-1.06%)    | 💵 **$100 Trade:** `-295 PKR` profit | Fees: `42 PKR`<br>📌 **$35 Ref:** `-103 PKR` profit | Fees: `15 PKR` | 🔴 LOSS                 |
| OPUSDT   | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-08 05:45:00 PKT (00:45:00 UTC) | 2026-09-08 06:01:21 PKT (01:01:21 UTC) | $0.1120<br><small>2026-09-08 06:01:21 PKT (01:01:21 UTC)</small>   | $0.1132<br><small>-</small>                                      | $0.1141<br><small>-</small>                                      | 2026-09-08 07:45:28 PKT (02:45:28 UTC) | -2.07 (-2.07%)    | 💵 **$100 Trade:** `-575 PKR` profit | Fees: `41 PKR`<br>📌 **$35 Ref:** `-201 PKR` profit | Fees: `14 PKR` | 🔴 LOSS                 |
| ALGOUSDT | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-08 04:00:00 PKT (23:00:00 UTC) | 2026-09-08 04:16:10 PKT (23:16:10 UTC) | $0.0965<br><small>2026-09-08 04:16:10 PKT (23:16:10 UTC)</small>   | $0.0977<br><small>2026-09-08 05:15:32 PKT (00:15:32 UTC)</small> | $0.0984<br><small>-</small>                                      | 2026-09-08 05:30:33 PKT (00:30:33 UTC) | +0.57 (+0.57%)    | 💵 **$100 Trade:** `+160 PKR` profit | Fees: `42 PKR`<br>📌 **$35 Ref:** `+56 PKR` profit | Fees: `15 PKR`  | 🟢 PARTIAL WIN          |
| FETUSDT  | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-08 00:15:00 PKT (19:15:00 UTC) | 2026-09-08 00:31:12 PKT (19:31:12 UTC) | $0.1862<br><small>2026-09-08 00:31:12 PKT (19:31:12 UTC)</small>   | $0.1884<br><small>-</small>                                      | $0.1906<br><small>-</small>                                      | 2026-09-08 03:30:33 PKT (22:30:33 UTC) | -2.67 (-2.67%)    | 💵 **$100 Trade:** `-742 PKR` profit | Fees: `41 PKR`<br>📌 **$35 Ref:** `-260 PKR` profit | Fees: `14 PKR` | 🔴 LOSS                 |
| APTUSDT  | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-07 17:45:00 PKT (12:45:00 UTC) | 2026-09-07 18:01:16 PKT (13:01:16 UTC) | $0.6423<br><small>2026-09-07 18:01:16 PKT (13:01:16 UTC)</small>   | $0.6497<br><small>-</small>                                      | $0.6548<br><small>-</small>                                      | 2026-09-07 20:45:29 PKT (15:45:29 UTC) | -2.30 (-2.30%)    | 💵 **$100 Trade:** `-639 PKR` profit | Fees: `41 PKR`<br>📌 **$35 Ref:** `-224 PKR` profit | Fees: `14 PKR` | 🔴 LOSS                 |
| DYDXUSDT | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-07 18:45:00 PKT (13:45:00 UTC) | 2026-09-07 19:01:36 PKT (14:01:36 UTC) | $0.1245<br><small>2026-09-07 19:01:36 PKT (14:01:36 UTC)</small>   | $0.1259<br><small>-</small>                                      | $0.1269<br><small>-</small>                                      | 2026-09-07 20:30:34 PKT (15:30:34 UTC) | -1.80 (-1.81%)    | 💵 **$100 Trade:** `-499 PKR` profit | Fees: `41 PKR`<br>📌 **$35 Ref:** `-175 PKR` profit | Fees: `14 PKR` | 🔴 LOSS                 |
| OPUSDT   | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-07 18:15:00 PKT (13:15:00 UTC) | 2026-09-07 18:31:11 PKT (13:31:11 UTC) | $0.1121<br><small>2026-09-07 18:31:11 PKT (13:31:11 UTC)</small>   | $0.1132<br><small>2026-09-07 20:00:46 PKT (15:00:46 UTC)</small> | $0.1141<br><small>-</small>                                      | 2026-09-07 20:15:31 PKT (15:15:31 UTC) | +0.53 (+0.53%)    | 💵 **$100 Trade:** `+146 PKR` profit | Fees: `42 PKR`<br>📌 **$35 Ref:** `+51 PKR` profit | Fees: `15 PKR`  | 🟢 PARTIAL WIN          |
| XRPUSDT  | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-07 17:45:00 PKT (12:45:00 UTC) | 2026-09-07 18:01:07 PKT (13:01:07 UTC) | $1.4126<br><small>2026-09-07 18:01:07 PKT (13:01:07 UTC)</small>   | $1.4289<br><small>-</small>                                      | $1.4402<br><small>-</small>                                      | 2026-09-07 19:15:30 PKT (14:15:30 UTC) | -0.95 (-0.95%)    | 💵 **$100 Trade:** `-263 PKR` profit | Fees: `42 PKR`<br>📌 **$35 Ref:** `-92 PKR` profit | Fees: `15 PKR`  | 🔴 LOSS                 |
| ETHUSDT  | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-07 17:45:00 PKT (12:45:00 UTC) | 2026-09-07 18:01:03 PKT (13:01:03 UTC) | $2,507.34<br><small>2026-09-07 18:01:03 PKT (13:01:03 UTC)</small> | $2,535.55<br><small>-</small>                                    | $2,555.59<br><small>-</small>                                    | 2026-09-07 19:15:29 PKT (14:15:29 UTC) | -0.79 (-0.79%)    | 💵 **$100 Trade:** `-219 PKR` profit | Fees: `42 PKR`<br>📌 **$35 Ref:** `-76 PKR` profit | Fees: `15 PKR`  | 🔴 LOSS                 |
| SOLUSDT  | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-07 17:45:00 PKT (12:45:00 UTC) | 2026-09-07 18:01:04 PKT (13:01:04 UTC) | $105.7629<br><small>2026-09-07 18:01:04 PKT (13:01:04 UTC)</small> | $107.0089<br><small>-</small>                                    | $107.8548<br><small>-</small>                                    | 2026-09-07 18:45:29 PKT (13:45:29 UTC) | -0.94 (-0.94%)    | 💵 **$100 Trade:** `-261 PKR` profit | Fees: `42 PKR`<br>📌 **$35 Ref:** `-91 PKR` profit | Fees: `15 PKR`  | 🔴 LOSS                 |
| AXSUSDT  | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-07 17:15:00 PKT (12:15:00 UTC) | 2026-09-07 17:31:25 PKT (12:31:25 UTC) | $0.9675<br><small>2026-09-07 17:31:25 PKT (12:31:25 UTC)</small>   | $0.9786<br><small>2026-09-07 18:00:43 PKT (13:00:43 UTC)</small> | $0.9863<br><small>2026-09-07 18:30:35 PKT (13:30:35 UTC)</small> | -                                      | +1.42 (+1.42%)    | 💵 **$100 Trade:** `+395 PKR` profit | Fees: `42 PKR`<br>📌 **$35 Ref:** `+138 PKR` profit | Fees: `15 PKR` | 🟢 FULL WIN             |
| FILUSDT  | S3_VOLATILITY_SQUEEZE | **15m**                 | 2026-09-07 17:00:00 PKT (12:00:00 UTC) | 2026-09-07 17:16:07 PKT (12:16:07 UTC) | $0.8273<br><small>2026-09-07 17:16:07 PKT (12:16:07 UTC)</small>   | $0.8364<br><small>2026-09-07 17:45:31 PKT (12:45:31 UTC)</small> | $0.8430<br><small>-</small>                                      | 2026-09-07 18:00:43 PKT (13:00:43 UTC) | +0.55 (+0.55%)    | 💵 **$100 Trade:** `+153 PKR` profit | Fees: `42 PKR`<br>📌 **$35 Ref:** `+53 PKR` profit | Fees: `15 PKR`  | 🟢 PARTIAL WIN          |

---

## 🧠 Active Phase 1 Strategies
- **I1: Multi-Timeframe Trend + Volatility Pullback (4H Trend + 1H Execution)**
- **I2: Cross-Sectional Momentum & Relative Strength Rotation (1D Top Decile Ranker)**
- **S3: Volatility Squeeze Breakout (15m Bollinger-Keltner + OBV)**

*Note: All milestones (Zone Formation, Signal Generation, Entry, TP1, TP2, SL) are tracked with exact Pakistan Standard Time (PKT) and UTC timestamps. PKR calculations are for informational reference only.*
