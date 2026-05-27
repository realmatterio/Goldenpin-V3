#!/usr/bin/env python3
"""
Golden Pin Analyzer — 深度分析引擎
Data source: workspace-stock-goldenpin
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
DATA_DIR = Path("/Users/ttse/.openclaw/workspace-stock-goldenpin/data/Golden Pin Stockbot - OpenClaw")
OUTPUT_DIR = Path(__file__).parent.parent / "output"

CAPITULATION_MAX_DROP_30D = 0.25
TIER_THRESHOLDS = {4: "S+⚡⚡", 3: "S+⚡", 2: "S+", 1: "S"}
TRANCHE_PCT = [0.30, 0.40, 0.30]

# V3 14 Indicators
LONG_HK = ["L17", "L16", "L06", "L04", "L03"]
SHO_HK = ["S02", "S01", "S11"]
LONG_US = ["US01", "US02", "US03"]
SHO_US = ["US04", "US05", "US06"]

# ── Data Loading ──────────────────────────────────────────────────────────────
def load_all_data():
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")
    dfs = []
    for f in sorted(DATA_DIR.glob("StockDailyPins*.csv*")):
        try:
            df = pd.read_csv(f)
            if "GoldGateOnAlgo1" not in df.columns:
                df["GoldGateOnAlgo1"] = "N"
                df["GoldGateOnAlgo2"] = "N"
            dfs.append(df)
        except Exception as e:
            print(f"⚠️ Error loading {f.name}: {e}")
    if not dfs:
        raise ValueError("No CSV files found")
    result = pd.concat(dfs, ignore_index=True)
    result["Date"] = pd.to_datetime(result["Date"])
    return result.sort_values(["Stock_No", "Date"]).reset_index(drop=True)

def flag_signals(df):
    for col in ["GoldenPinDown", "GoldenPinUp", "BluePinUp", "BluePinDown",
                "WeakToStrong", "StrongToWeak", "GreyPinDown",
                "GoldGateOnAlgo1", "GoldGateOnAlgo2"]:
        if col in df.columns:
            df[f"is_{col}"] = df[col] == "Y"
    return df

def capitulation_filter(df):
    df = df.copy()
    df = df.sort_values(["Stock_No", "Date"])
    df["close_30d_ago"] = df.groupby("Stock_No")["Close"].shift(30)
    df["return_30d"] = (df["Close"] - df["close_30d_ago"]) / df["close_30d_ago"]
    df["drop_30d_pct"] = -df["return_30d"]
    df["blueup_7d"] = df.groupby("Stock_No")["is_BluePinUp"].rolling(7, min_periods=1).sum().reset_index(level=0, drop=True)
    df["blueup_14d"] = df.groupby("Stock_No")["is_BluePinUp"].rolling(14, min_periods=1).sum().reset_index(level=0, drop=True)
    df["blueup_30d"] = df.groupby("Stock_No")["is_BluePinUp"].rolling(30, min_periods=1).sum().reset_index(level=0, drop=True)
    df["w2s_7d"] = df.groupby("Stock_No")["is_WeakToStrong"].rolling(7, min_periods=1).sum().reset_index(level=0, drop=True)
    df["has_institutional_support"] = (df["blueup_7d"] > 0) | (df["w2s_7d"] > 0)
    df["drop_under_25pct"] = df["drop_30d_pct"] < CAPITULATION_MAX_DROP_30D
    df["goldDn_filtered"] = df["is_GoldenPinDown"] & df["has_institutional_support"] & df["drop_under_25pct"]
    return df

def tier_enhancement(df, window=30):
    df = df.copy()
    df["goldDn_30d_count"] = df.groupby("Stock_No")["is_GoldenPinDown"].rolling(window, min_periods=1).sum().reset_index(level=0, drop=True).astype(int)
    df["tier"] = df["goldDn_30d_count"].apply(lambda x: TIER_THRESHOLDS.get(x, "S+⚡⚡") if x >= 1 else None)
    df.loc[~df["is_GoldenPinDown"], "tier"] = None
    return df

def classify_indicators(df):
    """V3.2 Indicators — 基於逆向工程 V2 驗證更新 (2026-05-20)
    
    修正項目：
    - L17: Cap + Tier=S+⚡⚡ + RSI<45 + Blue14d≥2 (最嚴格 LONG)
    - L16: Cap + Tier≥S+⚡ + RSI<45 + W2S7d≥1 (高概率 LONG)
    - L06: GoldDn + W2S (無Cap, W2S=反轉信號)
    - L04: GoldDn + GoldGate1 (無Cap, 獨立算法)
    - L03: Cap + RSI<45 + W2S7d≥1 (基礎 LONG)
    - S02: Blue30d≤1 + RSI>60 + Drop>15% (最嚴格 SHO, 75%勝率)
    - S01: Blue7d=0 + RSI>65 (高位派貨)
    - S11: Blue14d=0 + RSI>60 + Drop>10% (67%勝率)
    - US01: GoldDn + Tier=S+⚡⚡ (無Cap)
    - US02: GoldDn + W2S (無Cap)
    - US03: GoldDn + GoldGate1 (無Cap)
    - US04: Blue14d=0 + RSI>60 (美股 SHO)
    - US05: Blue14d=0 (70%勝率)
    - US06: Blue7d=0 + RSI>55 (美股 SHO)
    """
    df = df.copy()
    conditions = []
    
    # HK LONG
    # L17: Cap + Tier=S+⚡⚡ + RSI<45 + Blue14d≥2
    conditions.append(("L17", (df["Country"] == "HK") & df["goldDn_filtered"] & (df["tier"] == "S+⚡⚡") & (df["RSI"] < 45) & (df["blueup_14d"] >= 2)))
    # L16: Cap + Tier≥S+⚡ + RSI<45 + W2S7d≥1
    conditions.append(("L16", (df["Country"] == "HK") & df["goldDn_filtered"] & (df["tier"].isin(["S+⚡", "S+⚡⚡"])) & (df["RSI"] < 45) & (df["w2s_7d"] >= 1)))
    # L06: GoldDn + W2S (無Cap)
    conditions.append(("L06", (df["Country"] == "HK") & df["is_GoldenPinDown"] & df["is_WeakToStrong"]))
    # L04: GoldDn + GoldGate1 (無Cap)
    conditions.append(("L04", (df["Country"] == "HK") & df["is_GoldenPinDown"] & (df["GoldGateOnAlgo1"] == "Y")))
    # L03: Cap + RSI<45 + W2S7d≥1
    conditions.append(("L03", (df["Country"] == "HK") & df["goldDn_filtered"] & (df["RSI"] < 45) & (df["w2s_7d"] >= 1)))
    
    # HK SHO
    # S02: Blue30d≤1 + RSI>60 + Drop>15% (75%勝率)
    conditions.append(("S02", (df["Country"] == "HK") & df["is_GoldenPinUp"] & (df["blueup_30d"] <= 1) & (df["RSI"] > 60) & (df["drop_30d_pct"] > 0.15)))
    # S01: Blue7d=0 + RSI>65
    conditions.append(("S01", (df["Country"] == "HK") & df["is_GoldenPinUp"] & (df["blueup_7d"] == 0) & (df["RSI"] > 65)))
    # S11: Blue14d=0 + RSI>60 + Drop>10% (67%勝率)
    conditions.append(("S11", (df["Country"] == "HK") & df["is_GoldenPinUp"] & (df["blueup_14d"] == 0) & (df["RSI"] > 60) & (df["drop_30d_pct"] > 0.10)))
    
    # US LONG (無Cap)
    conditions.append(("US01", (df["Country"] == "US") & df["is_GoldenPinDown"] & (df["tier"] == "S+⚡⚡")))
    conditions.append(("US02", (df["Country"] == "US") & df["is_GoldenPinDown"] & df["is_WeakToStrong"]))
    conditions.append(("US03", (df["Country"] == "US") & df["is_GoldenPinDown"] & (df["GoldGateOnAlgo1"] == "Y")))
    
    # US SHO
    conditions.append(("US04", (df["Country"] == "US") & df["is_GoldenPinUp"] & (df["blueup_14d"] == 0) & (df["RSI"] > 60)))
    conditions.append(("US05", (df["Country"] == "US") & df["is_GoldenPinUp"] & (df["blueup_14d"] == 0)))
    conditions.append(("US06", (df["Country"] == "US") & df["is_GoldenPinUp"] & (df["blueup_7d"] == 0) & (df["RSI"] > 55)))
    
    for name, cond in conditions:
        df[f"ind_{name}"] = cond
    
    return df

def calc_tranche_prices(df):
    df = df.copy()
    df["tranche1_price"] = df["Close"]
    df["p50"] = (df["High"] + df["Low"]) / 2
    df["p25"] = df["Low"] + 0.25 * (df["High"] - df["Low"])
    df["tranche2_price"] = df["p50"]
    df["tranche3_price"] = df["p25"]
    df["avg_entry_price"] = (df["tranche1_price"] * 0.30 + df["tranche2_price"] * 0.40 + df["tranche3_price"] * 0.30)
    return df

def backtest_goldDn_signals(df, hold_days=5):
    results = []
    signals = df[df["goldDn_filtered"]].copy()
    
    for _, row in signals.iterrows():
        stock = row["Stock_No"]
        entry_date = row["Date"]
        entry_price = row["Close"]
        
        future = df[(df["Stock_No"] == stock) & (df["Date"] > entry_date)].sort_values("Date")
        if len(future) >= hold_days:
            exit_price = future.iloc[hold_days - 1]["Close"]
            pnl_pct = (exit_price - entry_price) / entry_price * 100
            results.append({
                "stock": stock, "country": row["Country"], "entry_date": entry_date,
                "pnl_pct": pnl_pct, "tier": row.get("tier", ""),
            })
    
    return pd.DataFrame(results) if results else pd.DataFrame()

def generate_report(df):
    lines = []
    lines.append("=" * 70)
    lines.append("📈 黃金針 V3 深度分析報告")
    lines.append("=" * 70)
    
    # Date Range
    lines.append(f"\n📅 數據範圍：{df['Date'].min().date()} 至 {df['Date'].max().date()}")
    lines.append(f"   總行數：{len(df):,} | 股票數：{df['Stock_No'].nunique()}")
    
    # Signal Counts
    lines.append("\n📊 信號總數")
    lines.append("-" * 40)
    for sig in ["is_GoldenPinDown", "is_GoldenPinUp", "is_BluePinUp", "is_WeakToStrong"]:
        count = int(df[sig].sum())
        lines.append(f"   {sig.replace('is_', '')}: {count:,}")
    
    # Capitulation Filter
    lines.append("\n🛡️ Capitulation Filter")
    lines.append("-" * 40)
    total_goldDn = int(df["is_GoldenPinDown"].sum())
    filtered_goldDn = int(df["goldDn_filtered"].sum())
    filter_rate = (1 - filtered_goldDn / total_goldDn * 100) if total_goldDn > 0 else 0
    lines.append(f"   原始 GoldDn: {total_goldDn:,}")
    lines.append(f"   過濾後 GoldDn: {filtered_goldDn:,}")
    lines.append(f"   過濾率：{filter_rate:.1f}%")
    
    # Tier Distribution
    lines.append("\n⚡ Tier 分佈")
    lines.append("-" * 40)
    goldDn_df = df[df["is_GoldenPinDown"]]
    if "tier" in goldDn_df.columns:
        tier_counts = goldDn_df["tier"].value_counts()
        for tier in ["S+⚡⚡", "S+⚡", "S+", "S"]:
            lines.append(f"   {tier}: {tier_counts.get(tier, 0):,}")
    
    # Indicator Counts
    lines.append("\n🎯 V3 14 Indicators 信號")
    lines.append("-" * 40)
    ind_cols = [c for c in df.columns if c.startswith("ind_")]
    for col in sorted(ind_cols):
        name = col.replace("ind_", "")
        count = int(df[col].sum())
        if count > 0:
            lines.append(f"   {name}: {count:,}")
    
    # Market Distribution
    lines.append("\n🌍 按市場分佈")
    lines.append("-" * 40)
    for country in df["Country"].unique():
        c_data = df[df["Country"] == country]
        gdn = int(c_data["is_GoldenPinDown"].sum())
        filtered = int(c_data["goldDn_filtered"].sum())
        lines.append(f"   {country}: {len(c_data):,} 行 | GoldDn={gdn:,} Filtered={filtered:,}")
    
    # Backtest
    lines.append("\n🔄 簡單回測 (GoldDn Filtered, 5日持有)")
    lines.append("-" * 40)
    bt = backtest_goldDn_signals(df, hold_days=5)
    if len(bt) > 0:
        lines.append(f"   交易次數：{len(bt):,}")
        lines.append(f"   勝率：{(bt['pnl_pct'] > 0).mean():.1%}")
        lines.append(f"   平均回報：{bt['pnl_pct'].mean():+.2f}%")
        lines.append(f"   中位數回報：{bt['pnl_pct'].median():+.2f}%")
    
    return "\n".join(lines)

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("📥 載入數據...")
    df = load_all_data()
    
    print("🔧 處理信號...")
    df = flag_signals(df)
    df = capitulation_filter(df)
    df = tier_enhancement(df)
    df = classify_indicators(df)
    df = calc_tranche_prices(df)
    
    print("📊 生成報告...\n")
    report = generate_report(df)
    print(report)
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    output_path.write_text(report, encoding="utf-8")
    print(f"\n💾 報告已保存至 {output_path}")
