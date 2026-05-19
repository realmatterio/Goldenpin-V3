Preface_0000 - 黃金針系統概述

*日期：* 2026-05-18
*來源：* Danny Sir Daily Pin Signals
*整理：* AI 助手

───

📖 Preface_0000 理解摘要

黃金針系統核心邏輯

*1️⃣ 黃金針係追蹤機構資金流向*

• 🟡 GoldDn = 智錢撈底（低價吸納）
• 🔵 BlueUp = 機構持續买入
• ⚡ W2S = 動能反轉向上
• 🔴 GoldUp = 派貨（高位出貨）

*2️⃣ 問題：Raw signals 太混乱*

每日 50-100 隻股票有信號，唔知邊個係真正機會、邊個係陷阱（接刀）

*3️⃣ V3 系統的解決方案*

```
| 組成部分                      | 功能                           |
| ------------------------- | ---------------------------- |
| 14 個 Validated Indicators | 過濾無效信號，只保留高概率                |
| Capitulation Filter       | 確保唔係接刀（要有 7 日 BlueUp/W2S 支持） |
| Tier Enhancement          | GoldDn 30 日出現次數越多 = 信號越強     |
| 3-Tranche Orders          | 分批买入，降低成本                    |
```
*4️⃣ 最重要嘅洞察*

V3 系統的價值 = 警告幾時唔好買

歷史案例證明：

• 跟 V3 警告 → 避免 60-92% 損失
• 忽略 V3 警告 → 嚴重損失

───

📊 黃金針係咩？

Danny Sir 嘅 daily pin signals 每日篩出 4 類 institutional signals:

• 🟡 *GoldenPinDown 黃金針下* = 智錢撈底信號
• 🔵 *BluePinUp 藍針上* = 機構持續吸納
• ⚡ *WeakToStrong (W2S)* = 動能反轉向上
• 🔴 *GoldenPinUp 黃金針上* = 派貨警告

───

💎 點解有 Value?

• 唔係街市消息, 係追蹤 institutional flow
• Free public data (Google Drive)
• 涵蓋 港股 + 美股 + A股
• Daily refresh

⚠️ Raw Signals 的限制

• ❌ 信號太多 (每日 50-100 隻 stocks)
• ❌ 唔知邊個 priority
• ❌ 容易混入 false signals (接刀)
• ❌ 散戶睇唔晒, 又唔識篩

───

🦞 V3 系統 - Raw Pin Signals 轉化為 Actionable Trading System

✅ 14 個 Validated Indicators

```
| 類別 | LONG                             | SHO                     |
| --- | -------------------------------- | ----------------------- |
| 港股 | L17 / L16 / L06 / L04 / L03 (5個) | S02 / S01 / S11 (3個)    |
| 美股 | US01 / US02 / US03 (3個)          | US04 / US05 / US06 (3個) |
```
🛡️ Capitulation Filter (核心)

過濾接刀 trap,必須同時滿足:

• 必須有 7日 BluePinUp 或 W2S 證據
• 30日跌幅 < 25%
• 純 RSI 低 ≠ buy signal

⚡ Tier Enhancement (信號強度)

GoldDn 30日出現次數決定 Tier 升級:

```
| 出現次數 | 等級    | 強度   |
| ---- | ----- | ---- |
| 4次+  | S+ ⚡⚡ | 最強   |
| 3次   | S+ ⚡  | 強    |
| 2次   | S+    | 中強   |
| 1次   | S     | base |
```
📊 3-Tranche Limit Orders

• 30% 即時執行
• 40% 於 P50 執行
• 30% 於 P25 執行

= 分批撈, 平均成本最佳

📋 8 大紀律

• 業績前 7日不開 SHO
• 倉位 ≤ 5%
• 等...

───

🏆 V3 系統 推薦命中 trades

✅ 成功案例

```
| 股票            | 類型   | 收益           | Trigger                                         |
| ------------- | ---- | ------------ | ----------------------------------------------- |
| EBAY Call     | Long | +309% 🚀🚀🚀 | V3 US01+US02 雙 trigger,Entry $3.70 → 平倉 @ $8.60 |
| 1024 快手期權     | Long | +147%        | V3 L17 Tier S+ ⚡⚡,Entry $1.58 → 平 @ $4.62       |
| MCHP Call     | Long | +155%        | V3 US02 Pre-earnings,Entry $5.30 → 平 @ $13.52   |
| F (Ford) Call | Long | +6% (early)  | V3 US02 新 trigger,仲在運行中                         |
```
❌ V3 警告 (跟咗 = 避免損失)

```
| 股票      | 方向  | 損失   | V3 警告內容                             |
| ------- | --- | ---- | ----------------------------------- |
| AAL Put | Put | -92% | V3 早警告業績前 SHO,用戶 ignore             |
| GM Put  | Put | -60% | 同上,用戶 ignore                        |
| 阿里健康    | Put | -41% | V3 警告 RSI 唔達 capitulation,用戶 ignore |
```
───

📌 關鍵洞察

*跟咗 V3 警告 → 避免損失*
*忽略 V3 警告 → 嚴重損失*

V3 系統嘅價值唔在於推薦幾時買，而係警告幾時唔好買。

───

_文件整理自 2026-05-18 上午 6:01 WhatsApp 對話_
_workspace: workspace-stock-goldenpin_

───

*📌 總結：* 呢份文件係 Goldenpin V3 系統嘅核心說明書，解釋咗點將 Danny Sir 嘅 Raw Pin Signals 轉化為可執行嘅交易系統。
