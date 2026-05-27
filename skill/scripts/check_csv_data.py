#!/usr/bin/env python3
"""
CSV 數據質量檢查
檢查讀取過程有無錯誤
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path("/Users/ttse/.openclaw/workspace-stock-goldenpin/data/Golden Pin Stockbot - OpenClaw")

print("=" * 70)
print("📋 CSV 數據質量檢查")
print("=" * 70)

# ── 1. 檢查文件編碼 ─────────────────────────────────────────────────────────
print("\n🔍 1. 文件編碼檢查")
csv_files = list(DATA_DIR.glob("StockDailyPins*.csv*"))
if not csv_files:
    print("   ❌ 找不到 CSV 文件")
    exit(1)

file_path = csv_files[0]
print(f"   檢查文件：{file_path.name}")

# 嘗試唔同編碼
for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'big5']:
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            f.read(1000)
        print(f"   ✅ 編碼：{encoding}")
        break
    except:
        print(f"   ❌ 編碼：{encoding} 失敗")

# ── 2. 檢查原始內容 ────────────────────────────────────────────────────────
print("\n🔍 2. 原始內容檢查 (頭 5 行)")
with open(file_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i < 5:
            print(f"   行{i+1}: {repr(line[:200])}")

# ── 3. 檢查 CSV 結構 ───────────────────────────────────────────────────────
print("\n🔍 3. CSV 結構檢查")
df = pd.read_csv(file_path)
print(f"   總行數：{len(df):,}")
print(f"   總列數：{len(df.columns)}")
print(f"   列名：{list(df.columns)}")

# ── 4. 檢查數據類型 ────────────────────────────────────────────────────────
print("\n🔍 4. 數據類型檢查")
print(df.dtypes.to_string())

# ── 5. 檢查缺失值 ──────────────────────────────────────────────────────────
print("\n🔍 5. 缺失值檢查")
missing = df.isna().sum()
missing_pct = (df.isna().sum() / len(df) * 100).round(2)
missing_df = pd.DataFrame({'缺失數量': missing, '缺失百分比': missing_pct})
print(missing_df[missing_df['缺失數量'] > 0].to_string())

# ── 6. 檢查 GoldenPinDown 分佈 ─────────────────────────────────────────────
print("\n🔍 6. GoldenPinDown 分佈檢查")
print(f"   唯一值：{df['GoldenPinDown'].unique()}")
print(f"   分佈:\n{df['GoldenPinDown'].value_counts()}")

# ── 7. 檢查 RSI 數據 ───────────────────────────────────────────────────────
print("\n🔍 7. RSI 數據檢查")
print(f"   最小值：{df['RSI'].min():.2f}")
print(f"   最大值：{df['RSI'].max():.2f}")
print(f"   平均值：{df['RSI'].mean():.2f}")
print(f"   中位數：{df['RSI'].median():.2f}")
print(f"   缺失值：{df['RSI'].isna().sum()}")

# ── 8. 檢查日期格式 ────────────────────────────────────────────────────────
print("\n🔍 8. 日期格式檢查")
print(f"   日期列類型：{df['Date'].dtype}")
dates = pd.to_datetime(df['Date'])
print(f"   日期範圍：{dates.min()} 至 {dates.max()}")
print(f"   有無無效日期：{dates.isna().sum()}")

# ── 9. 檢查成交量數據 ──────────────────────────────────────────────────────
print("\n🔍 9. 成交量數據檢查")
print(f"   Volume 列類型：{df['Volume'].dtype}")
print(f"   最小值：{df['Volume'].min():,.0f}")
print(f"   最大值：{df['Volume'].max():,.0f}")
print(f"   平均值：{df['Volume'].mean():,.0f}")
print(f"   有無負數：{(df['Volume'] < 0).sum()}")
print(f"   有無 0 值：{(df['Volume'] == 0).sum()}")

# ── 10. 檢查價格數據 ───────────────────────────────────────────────────────
print("\n🔍 10. 價格數據檢查")
for col in ['Open', 'High', 'Low', 'Close']:
    print(f"   {col}: min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}")

# ── 11. 檢查 OHLC 邏輯 ─────────────────────────────────────────────────────
print("\n🔍 11. OHLC 邏輯檢查 (High >= Low)")
invalid_ohlc = df[df['High'] < df['Low']]
print(f"   無效 OHLC 行數：{len(invalid_ohlc)}")
if len(invalid_ohlc) > 0:
    print(f"   樣本:\n{invalid_ohlc[['Stock_No', 'Date', 'Open', 'High', 'Low', 'Close']].head()}")

# ── 12. 檢查 GoldPinDownDiary ──────────────────────────────────────────────
print("\n🔍 12. GoldPinDownDiary 檢查")
print(f"   唯一值數量：{df['GoldPinDownDiary'].nunique()}")
print(f"   有無空值：{df['GoldPinDownDiary'].isna().sum()}")
print(f"   長度檢查 (應該=5):")
diary_len = df['GoldPinDownDiary'].astype(str).str.len()
print(f"      長度<5: {(diary_len < 5).sum()}")
print(f"      長度=5: {(diary_len == 5).sum()}")
print(f"      長度>5: {(diary_len > 5).sum()}")

# ── 13. 檢查獨立欄位與 Diary 是否一致 ─────────────────────────────────────
print("\n🔍 13. Diary 與獨立欄位一致性檢查")

def check_diary_consistency(row):
    """檢查 Diary 同獨立欄位是否一致"""
    diary = row['GoldPinDownDiary']
    if pd.isna(diary) or len(str(diary)) != 5:
        return None
    
    d1 = 'Y' if row['GoldenPinDown_1DayAgo'] == 'Y' else 'N'
    d2 = 'Y' if row['GoldenPinDown_2DayAgo'] == 'Y' else 'N'
    d3 = 'Y' if row['GoldenPinDown_3DayAgo'] == 'Y' else 'N'
    d4 = 'Y' if row['GoldenPinDown_4DayAgo'] == 'Y' else 'N'
    d5 = 'Y' if row['GoldenPinDown_5DayAgo'] == 'Y' else 'N'
    
    expected = f"{d1}{d2}{d3}{d4}{d5}"
    actual = str(diary).strip()
    
    return actual == expected

df['diary_check'] = df.apply(check_diary_consistency, axis=1)
check_result = df[df['diary_check'].notna()]
match_rate = check_result['diary_check'].mean()
print(f"   一致性匹配率：{match_rate:.1%}")
print(f"   不匹配行數：{(~check_result['diary_check']).sum()}")

# ── 14. 檢查每個股票嘅數據連續性 ─────────────────────────────────────────
print("\n🔍 14. 數據連續性檢查 (每隻股票)")

df['Date_parsed'] = pd.to_datetime(df['Date'])

stock_stats = []
for stock in df['Stock_No'].unique()[:10]:
    stock_df = df[df['Stock_No'] == stock].sort_values('Date_parsed')
    if len(stock_df) > 1:
        date_diff = stock_df['Date_parsed'].diff().dt.days.dropna()
        gaps = (date_diff > 1).sum()
        stock_stats.append({
            'Stock': stock,
            '行數': len(stock_df),
            '日期斷層': gaps,
        })

print(pd.DataFrame(stock_stats).to_string())

# ── 15. 總結 ───────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("📝 數據質量總結")
print("=" * 70)

issues = []
if df['RSI'].isna().sum() > 0:
    issues.append(f"⚠️ RSI 有 {df['RSI'].isna().sum()} 個缺失值")
if len(invalid_ohlc) > 0:
    issues.append(f"⚠️ 有 {len(invalid_ohlc)} 行 OHLC 無效")
if match_rate < 1.0:
    issues.append(f"⚠️ Diary 一致性只有 {match_rate:.1%}")
if (df['Volume'] == 0).sum() > 0:
    issues.append(f"⚠️ 有 {(df['Volume'] == 0).sum()} 行成交量為 0")

if issues:
    print("\n發現問題:")
    for issue in issues:
        print(f"   {issue}")
else:
    print("\n✅ 未發現明顯數據問題")
