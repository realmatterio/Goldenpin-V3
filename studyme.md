# 🦞 Goldenpin V3 Skill — 完整技術解說

## 📂 整體架構

```
┌─────────────────────────────────────────────────────────────────┐
│                    Google Drive 數據源                           │
│  https://drive.google.com/drive/folders/1cZcxnHdliAgj3WMW...    │
│  StockDailyPins(2024-2026).csv — Danny Sir 每日針位信號          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              workspace-stock-goldenpin/data/                     │
│  6 個 CSV 文件 (2024-2025 + 2026 年 1-5 月)                        │
│  52,767 行數據 | 1,586 隻股票 | HK/US/SZ/SS/ETF/Crypto/Gold      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              Goldenpin V3 Skill (4 個 Python 腳本)                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ dashboard.py │ │ analyzer.py  │ │ backtest.py  │            │
│  │ 每日儀表板   │ │ 深度分析     │ │ 回測引擎     │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OpenClaw Gateway                              │
│  WhatsApp 觸發 → Skill 匹配 → 執行腳本 → 返回結果                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 第一部分：SKILL.md 配置

🦞 Goldenpin V3 Skill — 完整技術解說

───

📂 一、SKILL.md 配置

*SKILL.md* 係 OpenClaw Skill 嘅「身份證」，定義：

```
| 字段   | 作用                                 |
| ---- | ---------------------------------- |
| 觸發短語 | 用戶講「黃金針」「Goldenpin」等自動匹配呢個 Skill   |
| 數據路徑 | 指向 workspace-stock-goldenpin/data/ |
| 功能描述 | 話畀 AI 知呢個 Skill 可以做咩               |
| 輸出格式 | 規範報告點樣呈現畀用戶                        |
```
───

🐍 二、Python 腳本詳解

*腳本 1: `dashboard.py` — 每日信號儀表板*

核心功能

生成 *今日* 嘅信號摘要，快速睇晒所有機會。

代碼結構

```
# ── 1. 配置 ─────────────────────────────────────────────
DATA_DIR = Path("/Users/ttse/.openclaw/workspace-stock-goldenpin/data/...")
CAPITULATION_MAX_DROP_30D = 0.25      # 30日跌幅 < 25%
TIER_THRESHOLDS = {4: "S+⚡⚡", 3: "S+⚡", 2: "S+", 1: "S"}
TRANCHE_PCT = [0.30, 0.40, 0.30]      # 3-Tranche 比例

# ── 2. 載入數據 ──────────────────────────────────────────
def load_all_data():
    dfs = []
    for f in DATA_DIR.glob("StockDailyPins*.csv*"):  # 讀所有 CSV
        df = pd.read_csv(f)
        dfs.append(df)
    return pd.concat(dfs)  # 合併成一個 DataFrame

# ── 3. 標記信號 ──────────────────────────────────────────
def flag_signals(df):
    # 將 "Y"/"N" 轉為 True/False
    df["is_GoldenPinDown"] = df["GoldenPinDown"] == "Y"
    df["is_BluePinUp"] = df["BluePinUp"] == "Y"
    # ... 其他信號
    return df

# ── 4. Capitulation Filter ───────────────────────────────
def capitulation_filter(df):
    # 計算 30 日跌幅
    df["drop_30d_pct"] = -(Close - Close_30d_ago) / Close_30d_ago
    
    # 計算 7 日 BluePinUp / W2S 計數
    df["blueup_7d"] = rolling_sum(is_BluePinUp, window=7)
    df["w2s_7d"] = rolling_sum(is_WeakToStrong, window=7)
    
    # 過濾條件
    df["goldDn_filtered"] = (
        is_GoldenPinDown & 
        (blueup_7d > 0 | w2s_7d > 0) &   # 有機構支持
        (drop_30d_pct < 0.25)             # 唔係暴跌接刀
    )
    return df

# ── 5. Tier Enhancement ──────────────────────────────────
def tier_enhancement(df):
    # 計算 30 日內 GoldDn 出現次數
    df["goldDn_30d_count"] = rolling_sum(is_GoldenPinDown, window=30)
    
    # 映射到 Tier
    df["tier"] = goldDn_30d_count.map({
        4+: "S+⚡⚡", 3: "S+⚡", 2: "S+", 1: "S"
    })
    return df

# ── 6. 3-Tranche 計算 ────────────────────────────────────
def calc_tranche_prices(df):
    df["T1"] = Close                    # 30% 即時
    df["T2"] = (High + Low) / 2         # 40% P50
    df["T3"] = Low + 0.25*(High-Low)    # 30% P25
    df["Avg"] = T1*0.3 + T2*0.4 + T3*0.3
    return df

# ── 7. 生成報告 ──────────────────────────────────────────
def generate_dashboard(df, date=None):
    target = date if date else df["Date"].max()  # 最新日期
    day = df[df["Date"] == target]
    
    # 輸出格式化的文字報告
    lines = []
    lines.append(f"🦞 黃金針 V3 每日信號儀表板 — {target}")
    lines.append(f"📊 信號總覽: {sum(day['is_GoldenPinDown'])}")
    lines.append(f"🏆 Top Signals: {day.sort_values('RSI').head(10)}")
    return "\n".join(lines)
```
執行流程

```
CSV 數據 → flag_signals → capitulation_filter → tier_enhancement 
       → calc_tranche_prices → generate_dashboard → 輸出
```
───

*腳本 2: `analyzer.py` — 深度分析引擎*

核心功能

將 Raw Signals 分類為 *14 個 V3 Indicators*，並生成完整統計。

14 Indicators 分類邏輯



2. *核心邏輯* → Capitulation Filter + Tier + 14 Indicators
3. *輸出* → 每日儀表板 / 深度分析 / 回測報告
4. *調用* → OpenClaw 自動匹配 + WhatsApp 觸發

*價值：* 將 Raw Signals 轉化為 *可執行交易信號*，過濾 81% 假信號，歷史勝率 ~45%。

有咩具體部分想深入了解？🔍
