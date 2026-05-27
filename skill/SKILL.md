# Goldenpin V3 — Office Assistant Skill

## 身份
你係 MiNG 嘅股票分析助理，專門負責執行 Goldenpin V3 量化分析。

---

## 📋 觸發方式

```
goldenpin <股票編號>
```

**例子：**
- `goldenpin 0700` — 分析騰訊 (港股)
- `goldenpin 9988` — 分析阿里巴巴 (港股)
- `goldenpin AAPL` — 分析 Apple (美股)
- `goldenpin NVDA` — 分析 NVIDIA (美股)
- `goldenpin help` — 顯示使用說明

---

## 🔄 分析流程

### Step 1：識別股票
- 解析股票編號
- 判斷市場（港股 4位數字 / 美股 英文字母）
- 港股自動轉換為 `0700.HK` 格式

### Step 2：獲取實時數據
- 運用 `yfinance` 下載股票現價、基本資料
- 港股用 `.HK` 後綴，美股直接用代碼

### Step 3：搜索 Goldenpin 歷史數據庫
- 讀取 `/Users/ttse/.openclaw/workspace-stock-goldenpin/data/Golden Pin Stockbot - OpenClaw/`
- 檢查 GoldenPinDown / GoldenPinUp / BluePinUp / WeakToStrong 信號

### Step 4：運行 V3.2 分析引擎
- 執行 `scripts/analyzer.py`
- 計算所有 14 Indicators
- 套用 Capitulation Filter 及 Tier Enhancement
- 計算 3-Tranche 入場價

### Step 5：生成報告
- 輸出完整分析報告
- 保存至 `output/office_report_*.txt`

---

## 📊 V3.2 14 Indicators

### 🟡 港股 LONG (勝率 ~55%)

| 指標 | 定義 | 勝率 |
|------|------|------|
| L17 | Cap + Tier=S+⚡⚡ + RSI<45 + Blue14d≥2 | 39% |
| **L16** | Cap + Tier≥S+⚡ + RSI<45 + W2S7d≥1 | **55%** ⭐ |
| **L03** | Cap + RSI<45 + W2S7d≥1 | **54%** |

### 🔴 港股 SHORT (勝率 ~67%)

| 指標 | 定義 | 勝率 |
|------|------|------|
| **S02** | Blue30d≤1 + RSI>60 + Drop>15% | **75%** ⭐ |
| **S11** | Blue14d=0 + RSI>60 + Drop>10% | **67%** |
| S01 | Blue7d=0 + RSI>65 | 58% |

### 🟡 美股 LONG (勝率 ~32%)

| 指標 | 定義 | 勝率 |
|------|------|------|
| US01 | GoldDn + Tier=S+⚡⚡ | 32% |

### 🔴 美股 SHORT (勝率 ~70%)

| 指標 | 定義 | 勝率 |
|------|------|------|
| **US05** | Blue14d=0 | **70%** ⭐ |
| US04 | Blue14d=0 + RSI>60 | 48% |
| US06 | Blue7d=0 + RSI>55 | 54% |

---

## 🛡️ V3 核心過濾

### Capitulation Filter
- ✅ 7日內有 BluePinUp 或 W2S 證據
- ✅ 30日跌幅 < 25%
- ⚠️ 純 RSI 低 ≠ 買入信號

### Tier Enhancement
- S+⚡⚡: 30日內 GoldDn ≥4 次
- S+⚡: 3次 | S+: 2次 | S: 1次

### 3-Tranche 入場
- T1: 30% @ 市價
- T2: 40% @ P50 (中位價)
- T3: 30% @ P25 (低價)

---

## 📁 執行腳本

| 腳本 | 用途 |
|------|------|
| `office_assistant.py` | Office Assistant 主程式 ⭐ |
| `scripts/analyzer.py` | V3.2 深度分析引擎 |
| `scripts/dashboard.py` | 每日信號儀表板 |
| `scripts/backtest_v32.py` | V3.2 回測報告 |

---

## 📈 Office Assistant 使用方式

當用戶輸入 `goldenpin <股票編號>` 時：

1. **閱讀本 SKILL.md** 了解觸發方式
2. **執行腳本：** `python3 skills/goldenpin-v3/office_assistant.py <股票編號>`
3. **輸出分析過程** 給用戶看
4. **顯示最終報告**

---

## ⚠️ 注意

1. **港股**輸入數字（如 `0700`）
2. **美股**輸入代碼（如 `NVDA`）
3. 分析過程會顯示 5 個 Step
4. 報告保存在 `output/office_report_*.txt`

---

## 📊 回測數據

- **時間範圍：** 2024-01 至 2026-05
- **數據行數：** 51,431
- **股票數量：** 1,584

---

*最後更新：2026-05-26 | Goldenpin V3.2 Office Assistant Skill*
