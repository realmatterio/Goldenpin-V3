# 🦞 Goldenpin V3.2 — 整體運作簡介

> **最後更新：** 2026-05-20 | **版本：** V3.2 | **回測期：** 2024-01 至 2026-05

---

## 🤖 系統係咩？

**Goldenpin** 係基於 Danny Sir 每日針位信號嘅量化交易系統。核心邏輯：

```
Raw Pin Signals (50-100隻/日)
        ↓
   Capitulation Filter (過濾接刀)
        ↓
   Tier Enhancement (信號強度分級)
        ↓
   14 Validated Indicators (精選高概率)
        ↓
   3-Tranche 入場價 (分批撈底)
        ↓
   交易信號輸出
```

---

## 📊 數據源

| 項目 | 說明 |
|------|------|
| **來源** | Danny Sir Google Drive CSV |
| **覆蓋** | 港股 + 美股 + A股 |
| **更新** | 每日 |
| **欄位** | Country, Stock_No, Date, Pin 信號, OHLCV, RSI 等 |

---

## 🛡️ 三大過濾機制

### 1️⃣ Capitulation Filter（防接刀）

| 條件 | 說明 |
|------|------|
| ✅ 7 日內有 BluePinUp 或 W2S | 有機構支持 |
| ✅ 30 日跌幅 < 25% | 唔係暴跌接刀 |
| ❌ 純 RSI 低 ≠ 買入 | 防止超賣陷阱 |

### 2️⃣ Tier Enhancement（信號強度）

| 30日內 GoldDn 次數 | Tier | 強度 |
|-------------------|------|------|
| ≥4 | S+⚡⚡ | 最強 |
| 3 | S+⚡ | 強 |
| 2 | S+ | 中強 |
| 1 | S | 基礎 |

### 3️⃣ 14 Validated Indicators（V3.2）

> ⚠️ V3.2 定義基於 2024-2026 歷史數據逆向工程驗證，唔係 Danny Sir 原始定義

#### 🟡 港股 LONG (5個)

| Ind | 定義 | 勝率 | PnL |
|-----|------|------|-----|
| L17 | Cap + Tier⚡⚡ + RSI<45 + Blue14d≥2 | 39% | +5.5% |
| **L16** | Cap + Tier≥S+⚡ + RSI<45 + W2S7d≥1 | **55%** | +7.5% |
| L06 | GoldDn + W2S | — | — |
| L04 | GoldDn + GoldGate1 | — | — |
| **L03** | Cap + RSI<45 + W2S7d≥1 | **54%** | +7.4% |

#### 🔴 港股 SHO (3個)

| Ind | 定義 | 勝率 | PnL |
|-----|------|------|-----|
| **S02** | Blue30d≤1 + RSI>60 + Drop>15% | **75%** 🔥 | +10% |
| S01 | Blue7d=0 + RSI>65 | 58% | -3.4% |
| **S11** | Blue14d=0 + RSI>60 + Drop>10% | **67%** 🔥 | +7.0% |

#### 🌎 美股 LONG (3個)

| Ind | 定義 | 勝率 |
|-----|------|------|
| US01 | GoldDn + Tier⚡⚡ (無Cap) | 32% |
| US02 | GoldDn + W2S (無Cap) | — |
| US03 | GoldDn + GoldGate1 (無Cap) | — |

#### 🌎 美股 SHO (3個)

| Ind | 定義 | 勝率 |
|-----|------|------|
| US04 | Blue14d=0 + RSI>60 | 48% |
| **US05** | Blue14d=0 | **70%** 🔥 |
| US06 | Blue7d=0 + RSI>55 | 54% |

---

## 📈 V3.2 回測結果摘要

### 回測參數
- **數據期：** 2024-01-02 至 2026-05-15
- **總行數：** 51,431 | **股票數：** 1,584
- **GoldDn 原始：** 9,219 | **Filtered：** 1,722 | **GoldUp：** 5,998

### LONG vs SHO 對比

| 方向 | V3 舊 | V3.2 新 | 提升 |
|------|-------|---------|------|
| LONG 平均勝率 | 36.5% | **44.9%** | +8.4% |
| SHO 平均勝率 | 59.7% | **62.0%** | +2.3% |

### 14 日持有（長期）

| Ind | 14日勝率 | 14日PnL |
|-----|---------|---------|
| L16 | **55%** | +14.1% |
| L03 | **55%** | +14.1% |
| L17 | 43% | +16.5% |
| S02 | **73%** | +8.8% |
| US05 | **77%** | +1.7% |

---

## 🔄 完整 Workflow

```
用戶：「今日有無黃金針信號？」
     ↓
OpenClaw 匹配 → 觸發 goldenpin-v3 skill
     ↓
執行 scripts/dashboard.py
     ↓
載入 CSV → flag_signals → capitulation_filter
     → tier_enhancement → classify_indicators (V3.2)
     → calc_tranche_prices
     ↓
生成儀表板 → 返回 WhatsApp
     ↓
同時保存完整報告到 output/
```

---

## ⚠️ 重要聲明

1. **LONG 信號勝率 ~55%** 係抄底策略嘅自然上限，唔係 Bug
2. **SHO 信號勝率 67-75%** 係系統最有價值嘅部分 — **警告幾時唔好買**
3. **14 Indicators 定義係 AI 逆向工程推測**，唔係 Danny Sir 原始定義
4. **L06/L04/US02/US03** 歷史數據中無信號
5. **S02/S11 樣本數較少**（15-16 筆），需持續驗證
6. **過去表現 ≠ 未來保證**

---

## 📚 相關文檔

| 文檔 | 位置 | 說明 |
|------|------|------|
| Preface_0000.md | workspace-stock-goldenpin/ | V3 系統核心邏輯（Capitulation/Tier/3-Tranche） |
| Goldenpin_0000.md | workspace-stock-goldenpin/ | Google Drive 數據源說明 |
| SKILL.md | goldenpin-v3/ | 技能定義（含 V3.2 回測數據） |
| README.md | goldenpin-v3/ | **呢個文件** |

---

*Goldenpin V3.2 | 2026-05-20*