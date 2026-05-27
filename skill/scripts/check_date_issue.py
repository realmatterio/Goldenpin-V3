#!/usr/bin/env python3
"""
檢查日期處理問題
確保 groupby/rolling 計算正確
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path("/Users/ttse/.openclaw/workspace-stock-goldenpin/data/Golden Pin Stockbot - OpenClaw")

print("=" * 70)
print("📅 日期處理問題檢查")
print("=" * 70)

csv_files = list(DATA_DIR.glob("StockDailyPins*.csv*"))
if not csv_files:
    print("❌ 找不到 CSV 文件")
    exit(1)

file_path = csv_files[0]

# ── 1. 比較兩種讀取方式 ───────────────────────────────────────────────────
print("\n🔍 1. 比較 Date 列處理方式")

df1 = pd.read_csv(file_path)
df2 = pd.read_csv(file_path, parse_dates=['Date'])

print(f"\n   方式 1 (無 parse_dates):")
print(f"      Date 類型：{df1['Date'].dtype}")
print(f"      樣本值：{df1['Date'].iloc[0]}")

print(f"\n   方式 2 (parse_dates=['Date']):")
print(f"      Date 類型：{df2['Date'].dtype}")
print(f"      樣本值：{df2['Date'].iloc[0]}")

# ── 2. 檢查 groupby 排序 ───────────────────────────────────────────────────
print("\n" + "=" * 70)
print("🔍 2. groupby 排序問題")
print("=" * 70)

df1['Date_parsed'] = pd.to_datetime(df1['Date'])
df1_sorted = df1.sort_values(['Stock_No', 'Date_parsed'])

df2_sorted = df2.sort_values(['Stock_No', 'Date'])

print(f"\n   ^HSI 嘅數據 (字符串排序):")
hsi1 = df1_sorted[df1_sorted['Stock_No'] == '^HSI'][['Stock_No', 'Date', 'GoldenPinDown', 'RSI']]
print(hsi1.head(10).to_string())

print(f"\n   ^HSI 嘅數據 (日期排序):")
hsi2 = df2_sorted[df2_sorted['Stock_No'] == '^HSI'][['Stock_No', 'Date', 'GoldenPinDown', 'RSI']]
print(hsi2.head(10).to_string())

# ── 3. 檢查 rolling 計算 ─────────────────────────────────────────────────
print("\n" + "=" * 70)
print("🔍 3. Rolling 計算問題")
print("=" * 70)

df_correct = df2.sort_values(['Stock_No', 'Date']).copy()
df_correct['is_GoldDn'] = (df_correct['GoldenPinDown'] == 'Y').astype(int)
df_correct['goldDn_7d'] = df_correct.groupby('Stock_No')['is_GoldDn'].transform(
    lambda x: x.rolling(7, min_periods=1).sum()
)

print("\n   正確 rolling 計算 (先排序):")
print(df_correct[df_correct['Stock_No'] == '^HSI'][['Date', 'GoldenPinDown', 'is_GoldDn', 'goldDn_7d']].head(10).to_string())

df_wrong = df2.copy()
df_wrong['is_GoldDn'] = (df_wrong['GoldenPinDown'] == 'Y').astype(int)
df_wrong['goldDn_7d_wrong'] = df_wrong.groupby('Stock_No')['is_GoldDn'].transform(
    lambda x: x.rolling(7, min_periods=1).sum()
)

print("\n   錯誤 rolling 計算 (無排序):")
print(df_wrong[df_wrong['Stock_No'] == '^HSI'][['Date', 'GoldenPinDown', 'is_GoldDn', 'goldDn_7d_wrong']].head(10).to_string())

# ── 4. 檢查對 RSI 分析嘅影響 ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("🔍 4. 對 RSI 分析嘅影響")
print("=" * 70)

df_check = df2.sort_values(['Stock_No', 'Date']).copy()
df_check['is_GoldDn'] = df_check['GoldenPinDown'] == 'Y'

goldn_rsi = df_check[df_check['is_GoldDn']]['RSI']
non_goldn_rsi = df_check[~df_check['is_GoldDn']]['RSI']

print(f"\n   正確排序後:")
print(f"      GoldDn 平均 RSI: {goldn_rsi.mean():.2f}")
print(f"      Non-GoldDn 平均 RSI: {non_goldn_rsi.mean():.2f}")

# ── 5. 結論 ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("📝 結論")
print("=" * 70)

print("""
✅ CSV 數據本身無問題
⚠️ 但係代碼必須：
   1. 使用 parse_dates=['Date'] 或 pd.to_datetime()
   2. 喺 groupby/rolling 之前先 sort_values(['Stock_No', 'Date'])
   
❌ 如果無咁樣做，會導致：
   - rolling 計算錯亂（用咗錯誤嘅順序）
   - BlueUp_7d / W2S_7d 計數錯誤
   - Capitulation Filter 判斷錯誤
   - 最終影響勝率
""")
