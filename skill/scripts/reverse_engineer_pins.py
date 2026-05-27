#!/usr/bin/env python3
"""
Reverse Engineer Golden Pin & Blue Pin Algorithms
基於 CSV 數據推測 Danny Sir 嘅針位算法
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
DATA_DIR = Path("/Users/ttse/.openclaw/workspace-stock-goldenpin/data/Golden Pin Stockbot - OpenClaw")
OUTPUT_DIR = Path(__file__).parent.parent / "output"

# ── Load Data ─────────────────────────────────────────────────────────────────
def load_sample_data():
    """載入 2026-05 數據做樣本"""
    csv_files = list(DATA_DIR.glob("StockDailyPins*.csv*"))
    if not csv_files:
        raise FileNotFoundError("No CSV files found in data directory")
    
    df = pd.read_csv(csv_files[0])
    df["Date"] = pd.to_datetime(df["Date"])
    return df.sort_values(["Stock_No", "Date"]).reset_index(drop=True)

# ── Feature Engineering ───────────────────────────────────────────────────────
def add_price_features(df):
    """添加價格特徵"""
    df = df.copy()
    
    # 每日回報
    df["return"] = df.groupby("Stock_No")["Close"].pct_change()
    
    # N 日回報
    for n in [3, 5, 10, 20, 30]:
        df[f"return_{n}d"] = df.groupby("Stock_No")["Close"].pct_change(n)
    
    # N 日最低/最高價
    for n in [5, 10, 20, 30]:
        df[f"min_{n}d"] = df.groupby("Stock_No")["Low"].transform(
            lambda x: x.rolling(n, min_periods=1).min()
        )
        df[f"max_{n}d"] = df.groupby("Stock_No")["High"].transform(
            lambda x: x.rolling(n, min_periods=1).max()
        )
    
    # 距離 N 日低點/高點嘅百分比
    df["dist_from_20d_low"] = (df["Close"] - df["min_20d"]) / df["min_20d"]
    df["dist_from_20d_high"] = (df["Close"] - df["max_20d"]) / df["max_20d"]
    
    # 價格位置 (0=接近 20 日低，1=接近 20 日高)
    range_20d = df["max_20d"] - df["min_20d"]
    df["price_position_20d"] = (df["Close"] - df["min_20d"]) / range_20d.replace(0, np.nan)
    
    return df

def add_volume_features(df):
    """添加成交量特徵"""
    df = df.copy()
    
    # 成交量 MA
    for n in [5, 10, 20]:
        df[f"vol_ma{n}"] = df.groupby("Stock_No")["Volume"].transform(
            lambda x: x.rolling(n, min_periods=1).mean()
        )
    
    # 成交量比率
    df["vol_ratio_5d"] = df["Volume"] / df["vol_ma5"]
    df["vol_ratio_10d"] = df["Volume"] / df["vol_ma10"]
    df["vol_ratio_20d"] = df["Volume"] / df["vol_ma20"]
    
    # N 日最高成交量
    df["vol_max_20d"] = df.groupby("Stock_No")["Volume"].transform(
        lambda x: x.rolling(20, min_periods=1).max()
    )
    df["vol_vs_20d_max"] = df["Volume"] / df["vol_max_20d"]
    
    return df

def add_rsi_features(df):
    """添加 RSI 特徵"""
    df = df.copy()
    
    # RSI 閾值
    df["rsi_below_30"] = df["RSI"] < 30
    df["rsi_below_40"] = df["RSI"] < 40
    df["rsi_below_50"] = df["RSI"] < 50
    df["rsi_above_70"] = df["RSI"] > 70
    
    # RSI 變化
    df["rsi_change"] = df.groupby("Stock_No")["RSI"].diff()
    df["rsi_change_3d"] = df.groupby("Stock_No")["RSI"].diff(3)
    
    # RSI N 日平均
    df["rsi_ma5"] = df.groupby("Stock_No")["RSI"].transform(
        lambda x: x.rolling(5, min_periods=1).mean()
    )
    
    return df

# ── Analysis Functions ────────────────────────────────────────────────────────
def analyze_golden_pin_down(df):
    """分析 GoldenPinDown 嘅特徵"""
    print("=" * 70)
    print("🟡 GoldenPinDown 算法分析")
    print("=" * 70)
    
    goldn = df[df["GoldenPinDown"] == "Y"]
    non_goldn = df[df["GoldenPinDown"] == "N"]
    
    print(f"\n📊 樣本分佈:")
    print(f"   GoldenPinDown=Y: {len(goldn):,} ({len(goldn)/len(df)*100:.2f}%)")
    print(f"   GoldenPinDown=N: {len(non_goldn):,}")
    
    # 1. RSI 分佈
    print(f"\n📈 RSI 分析:")
    print(f"   GoldDn 平均 RSI: {goldn['RSI'].mean():.2f}")
    print(f"   Non-GoldDn 平均 RSI: {non_goldn['RSI'].mean():.2f}")
    print(f"   GoldDn RSI < 30: {(goldn['RSI'] < 30).mean():.1%}")
    print(f"   GoldDn RSI < 40: {(goldn['RSI'] < 40).mean():.1%}")
    print(f"   GoldDn RSI < 50: {(goldn['RSI'] < 50).mean():.1%}")
    
    # 2. 價格回報
    print(f"\n📉 價格回報分析:")
    for col in ["return_3d", "return_5d", "return_10d", "return_20d", "return_30d"]:
        if col in goldn.columns:
            print(f"   GoldDn 平均{col.replace('return_', '')}: {goldn[col].mean():.2%}")
            print(f"   Non-GoldDn 平均{col.replace('return_', '')}: {non_goldn[col].mean():.2%}")
    
    # 3. 價格位置
    print(f"\n📍 價格位置分析:")
    print(f"   GoldDn 平均 price_position_20d: {goldn['price_position_20d'].mean():.2f}")
    print(f"   Non-GoldDn 平均 price_position_20d: {non_goldn['price_position_20d'].mean():.2f}")
    
    # 4. 成交量
    print(f"\n📊 成交量分析:")
    print(f"   GoldDn 平均 vol_ratio_20d: {goldn['vol_ratio_20d'].mean():.2f}")
    print(f"   Non-GoldDn 平均 vol_ratio_20d: {non_goldn['vol_ratio_20d'].mean():.2f}")
    
    # 5. GoldPinDownDiary 分析
    print(f"\n📔 GoldPinDownDiary 分析:")
    print(f"   GoldDn 時 Diary 分佈:")
    print(goldn["GoldPinDownDiary"].value_counts().head(10))

def analyze_blue_pin_up(df):
    """分析 BluePinUp 嘅特徵"""
    print("\n" + "=" * 70)
    print("🔵 BluePinUp 算法分析")
    print("=" * 70)
    
    blueup = df[df["BluePinUp"] == "Y"]
    non_blueup = df[df["BluePinUp"] == "N"]
    
    print(f"\n📊 樣本分佈:")
    print(f"   BluePinUp=Y: {len(blueup):,} ({len(blueup)/len(df)*100:.2f}%)")
    print(f"   BluePinUp=N: {len(non_blueup):,}")
    
    # 1. RSI 分佈
    print(f"\n📈 RSI 分析:")
    print(f"   BlueUp 平均 RSI: {blueup['RSI'].mean():.2f}")
    print(f"   Non-BlueUp 平均 RSI: {non_blueup['RSI'].mean():.2f}")
    
    # 2. 與 GoldenPinDown 嘅關係
    print(f"\n🔗 與 GoldenPinDown 嘅關係:")
    print(f"   BlueUp 時 GoldDn 同時=Y: {(blueup['GoldenPinDown'] == 'Y').mean():.1%}")
    print(f"   BlueUp 時 GoldDn 1 日前=Y: {(blueup['GoldenPinDown_1DayAgo'] == 'Y').mean():.1%}")
    print(f"   BlueUp 時 GoldDn 2 日前=Y: {(blueup['GoldenPinDown_2DayAgo'] == 'Y').mean():.1%}")
    
    # 3. 價格回報
    print(f"\n📉 價格回報分析:")
    for col in ["return_3d", "return_5d", "return_10d"]:
        if col in blueup.columns:
            print(f"   BlueUp 平均{col.replace('return_', '')}: {blueup[col].mean():.2%}")
            print(f"   Non-BlueUp 平均{col.replace('return_', '')}: {non_blueup[col].mean():.2%}")
    
    # 4. 成交量
    print(f"\n📊 成交量分析:")
    print(f"   BlueUp 平均 vol_ratio_20d: {blueup['vol_ratio_20d'].mean():.2f}")
    print(f"   Non-BlueUp 平均 vol_ratio_20d: {non_blueup['vol_ratio_20d'].mean():.2f}")
    
    # 5. 與 WeakToStrong 嘅關係
    print(f"\n⚡ 與 WeakToStrong 嘅關係:")
    print(f"   BlueUp 時 W2S 同時=Y: {(blueup['WeakToStrong'] == 'Y').mean():.1%}")

def analyze_weak_to_strong(df):
    """分析 WeakToStrong 嘅特徵"""
    print("\n" + "=" * 70)
    print("⚡ WeakToStrong 算法分析")
    print("=" * 70)
    
    w2s = df[df["WeakToStrong"] == "Y"]
    non_w2s = df[df["WeakToStrong"] == "N"]
    
    print(f"\n📊 樣本分佈:")
    print(f"   W2S=Y: {len(w2s):,} ({len(w2s)/len(df)*100:.2f}%)")
    
    # 1. RSI 變化
    print(f"\n📈 RSI 變化分析:")
    print(f"   W2S 平均 RSI 變化：{w2s['rsi_change'].mean():.2f}")
    print(f"   Non-W2S 平均 RSI 變化：{non_w2s['rsi_change'].mean():.2f}")
    print(f"   W2S 平均 RSI 變化_3d: {w2s['rsi_change_3d'].mean():.2f}")
    
    # 2. 價格回報
    print(f"\n📉 價格回報分析:")
    print(f"   W2S 平均 3 日回報：{w2s['return_3d'].mean():.2%}")
    print(f"   Non-W2S 平均 3 日回報：{non_w2s['return_3d'].mean():.2%}")
    print(f"   W2S 平均 5 日回報：{w2s['return_5d'].mean():.2%}")
    print(f"   Non-W2S 平均 5 日回報：{non_w2s['return_5d'].mean():.2%}")

def hypothesize_algorithms(df):
    """推測算法"""
    print("\n" + "=" * 70)
    print("🧠 算法推測")
    print("=" * 70)
    
    goldn = df[df["GoldenPinDown"] == "Y"]
    blueup = df[df["BluePinUp"] == "Y"]
    w2s = df[df["WeakToStrong"] == "Y"]
    
    print("\n🟡 GoldenPinDown 可能算法:")
    print("   條件 1: RSI < 40 (超賣)")
    print(f"         證據：{(goldn['RSI'] < 40).mean():.1%} 嘅 GoldDn 信號 RSI < 40")
    print("   條件 2: 股價處於 20 日低位附近")
    print(f"         證據：price_position_20d = {goldn['price_position_20d'].mean():.2f}")
    print("   條件 3: 30 日跌幅 > X% (可能 10-20%)")
    print(f"         證據：30 日回報 = {goldn['return_30d'].mean():.2%}")
    print("   條件 4: 成交量放大 (可能 > 1.5x 20 日平均)")
    print(f"         證據：vol_ratio_20d = {goldn['vol_ratio_20d'].mean():.2f}")
    
    print("\n🔵 BluePinUp 可能算法:")
    print("   條件 1: 之前有 GoldenPinDown 信號 (7 日內)")
    print(f"         證據：{(blueup['GoldenPinDown_1DayAgo'] == 'Y').mean():.1%} 1 日前有 GoldDn")
    print(f"         證據：{(blueup['GoldenPinDown_2DayAgo'] == 'Y').mean():.1%} 2 日前有 GoldDn")
    print("   條件 2: 價格反彈 (3-5 日回報 > 0)")
    print(f"         證據：3 日回報 = {blueup['return_3d'].mean():.2%}")
    print("   條件 3: RSI 回升")
    print(f"         證據：RSI 變化 = {blueup['rsi_change'].mean():.2f}")
    print("   條件 4: 成交量持續放大")
    print(f"         證據：vol_ratio_20d = {blueup['vol_ratio_20d'].mean():.2f}")
    
    print("\n⚡ WeakToStrong 可能算法:")
    print("   條件 1: RSI 由低回升 (RSI 變化 > 0)")
    print(f"         證據：RSI 變化 = {w2s['rsi_change'].mean():.2f}")
    print("   條件 2: 價格短期反彈 (3-5 日回報 > 5%?)")
    print(f"         證據：3 日回報 = {w2s['return_3d'].mean():.2%}")
    print("   條件 3: 可能與 BluePinUp 有重疊")
    print(f"         證據：{(w2s['BluePinUp'] == 'Y').mean():.1%} 同時有 BlueUp")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("📥 載入數據...")
    df = load_sample_data()
    
    print("🔧 添加特徵...")
    df = add_price_features(df)
    df = add_volume_features(df)
    df = add_rsi_features(df)
    
    print("🔍 開始分析...\n")
    analyze_golden_pin_down(df)
    analyze_blue_pin_up(df)
    analyze_weak_to_strong(df)
    hypothesize_algorithms(df)
    
    print("\n" + "=" * 70)
    print("💾 分析完成")
    print("=" * 70)
