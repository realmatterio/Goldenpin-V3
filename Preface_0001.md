好問題！讓我詳細對比 *Preface_0000.md 定義嘅 V3 系統* 同 *而家 Skill 實現* 嘅分別：

───

📊 對比分析表

```
| 組件                    | Preface_0000.md 定義               | 而家 Skill 實現                        | 狀態            |
| --------------------- | -------------------------------- | ---------------------------------- | ------------- |
| Capitulation Filter   |                                  |                                    |               |
| 7 日 BlueUp/W2S 證據     | ✅ 必須有                            | ✅ (blueup_7d > 0) | (w2s_7d > 0)   | ✅ 匹配          |
| 30 日跌幅 < 25%          | ✅                                | ✅ drop_30d_pct < 0.25              | ✅ 匹配          |
| 純 RSI 低 ≠ buy         | ✅ 警告                             | ⚠️ 未明確檢查                           | ⚠️ 需補充        |
| Tier Enhancement      |                                  |                                    |               |
| 4 次 + → S+⚡⚡          | ✅                                | ✅ TIER_THRESHOLDS = {4: "S+⚡⚡"}    | ✅ 匹配          |
| 3 次 → S+⚡             | ✅                                | ✅                                  | ✅ 匹配          |
| 2 次 → S+              | ✅                                | ✅                                  | ✅ 匹配          |
| 1 次 → S               | ✅                                | ✅                                  | ✅ 匹配          |
| 3-Tranche             |                                  |                                    |               |
| 30% 即時 @ Close        | ✅                                | ✅ tranche1 = Close                 | ✅ 匹配          |
| 40% P50 = (H+L)/2     | ✅                                | ✅ tranche2 = (High+Low)/2          | ✅ 匹配          |
| 30% P25 = L+0.25(H-L) | ✅                                | ✅ tranche3 = Low + 0.25*(High-Low) | ✅ 匹配          |
| 14 Indicators         |                                  |                                    |               |
| L17                   | GoldDn + S+⚡⚡ + BlueUp 7d≥3      | GoldDn + S+⚡⚡                      | ❌ 缺 BlueUp 條件 |
| L16                   | GoldDn + S+⚡/S+⚡⚡ + BlueUp 7d≥2  | GoldDn + S+⚡/S+⚡⚡                  | ❌ 缺 BlueUp 條件 |
| L06                   | GoldDn + W2S                     | ✅                                  | ✅ 匹配          |
| L04                   | GoldDn + GoldGate Algo1          | ✅                                  | ✅ 匹配          |
| L03                   | GoldDn + RSI 低                   | GoldDn + RSI<40                    | ⚠️ 閾值自定       |
| S02                   | GoldUp + StrongToWeak + drop>15% | GoldUp + StrongToWeak              | ❌ 缺跌幅條件       |
| S01                   | GoldUp + 無 BlueUp 7d             | ✅                                  | ✅ 匹配          |
| S11                   | GoldUp + drop>10%                | ✅                                  | ✅ 匹配          |
| US01-06               | 對應 HK 邏輯                         | ✅                                  | ✅ 匹配          |
```
───

⚠️ 發現嘅差異

1. *L17 缺 BlueUp 7d≥3 條件*

*Preface 定義：*

```
L17 = GoldDn + Tier S+⚡⚡ + BlueUp 7d ≥ 3
```
*而家代碼：*

```
cond_L17 = (HK) & goldDn_filtered & (tier == "S+⚡⚡")
# ❌ 無檢查 blueup_7d ≥ 3
```
*影響：* 可能將一啲無足夠機構支持嘅信號分類為 L17

───

2. *L16 缺 BlueUp 7d≥2 條件*

*Preface 定義：*

```
L16 = GoldDn + Tier S+⚡/S+⚡⚡ + BlueUp 7d ≥ 2
```
*而家代碼：*

```
cond_L16 = (HK) & goldDn_filtered & (tier.isin(["S+⚡", "S+⚡⚡"]))
# ❌ 無檢查 blueup_7d ≥ 2
```
───

3. *S02 缺跌幅>15% 條件*

*Preface 定義：*

```
S02 = GoldUp + StrongToWeak + drop > 15%
```
*而家代碼：*

```
cond_S02 = (HK) & is_GoldenPinUp & is_StrongToWeak
# ❌ 無檢查跌幅
```
───

4. *L03 RSI 閾值自定為 40*

*Preface 定義：*

```
L03 = GoldDn + RSI 低 (無指定數值)
```
*而家代碼：*

```
cond_L03 = (HK) & goldDn_filtered & (RSI < 40)
# ⚠️ 40 係自定閾值，Preface 無指定
```
───

5. *Capitulation Filter 未檢查「純 RSI 低 ≠ buy」*

*Preface 警告：*

```
純 RSI 低 ≠ buy signal
```
*而家代碼：*

```
df["goldDn_filtered"] = (
    is_GoldenPinDown & 
    has_institutional_support & 
    drop_under_25pct
)
# ⚠️ 無明確排除「純 RSI 低」情況
```
───

🔧 建議修復

如果你想個 Skill *完全匹配 Preface_0000.md*，可以咁樣改：
