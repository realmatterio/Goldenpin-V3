#!/usr/bin/env python3
"""
Golden Pin Dashboard — 每日信號儀表板
Data source: workspace-stock-goldenpin
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# ── Config: External Data Path ────────────────────────────────────────────────
DATA_DIR = Path("/Users/ttse/.openclaw/workspace-stock-goldenpin/data/Golden Pin Stockbot - OpenClaw")
OUTPUT_DIR = Path(__file__).parent.parent / "output"

# V3 Parameters
CAPITULATION_MAX_DROP_30D = 0.25
BLUEUP_MIN_DAYS = 7
TIER_THRESHOLDS = {4: "S+⚡⚡", 3: "S+⚡", 2: "S+", 1: "S"}
TRANCHE_PCT = [0.30, 0.40, 0.30]

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

# ── Signal Processing ─────────────────────────────────────────────────────────
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

def calc_tranche_prices(df):
    df = df.copy()
    df["tranche1_price"] = df["Close"]
    df["tranche1_pct"] = TRANCHE_PCT[0]
    df["p50"] = (df["High"] + df["Low"]) / 2
    df["p25"] = df["Low"] + 0.25 * (df["High"] - df["Low"])
    df["tranche2_price"] = df["p50"]
    df["tranche2_pct"] = TRANCHE_PCT[1]
    df["tranche3_price"] = df["p25"]
    df["tranche3_pct"] = TRANCHE_PCT[2]
    df["avg_entry_price"] = (df["tranche1_price"] * df["tranche1_pct"] + 
                              df["tranche2_price"] * df["tranche2_pct"] + 
                              df["tranche3_price"] * df["tranche3_pct"])
    return df

# ── Dashboard Generation ──────────────────────────────────────────────────────
def generate_dashboard(df, date=None):
    if date:
        target = pd.Timestamp(date)
    else:
        target = df["Date"].max()
    
    day = df[df["Date"] == target].copy()
    if day.empty:
        return f"❌ 沒有 {target.date()} 的數據"
    
    lines = []
    lines.append("=" * 70)
    lines.append(f"🦞 黃金針 V3 每日信號儀表板 — {target.strftime('%Y-%m-%d')}")
    lines.append("=" * 70)
    
    # Signal Summary
    lines.append("\n📊 信號總覽")
    lines.append("-" * 40)
    signals = {
        "🟡 GoldenPinDown": int(day["is_GoldenPinDown"].sum()),
        "🔴 GoldenPinUp": int(day["is_GoldenPinUp"].sum()),
        "🔵 BluePinUp": int(day["is_BluePinUp"].sum()),
        "⚡ WeakToStrong": int(day["is_WeakToStrong"].sum()),
    }
    for name, count in signals.items():
        lines.append(f"   {name}: {count}")
    lines.append(f"\n   🛡️ Capitulation Filter 通過：{int(day['goldDn_filtered'].sum())}")
    
    # Tier Distribution
    lines.append("\n⚡ Tier 等級分佈 (GoldDn)")
    lines.append("-" * 40)
    goldDn_day = day[day["is_GoldenPinDown"]]
    if "tier" in goldDn_day.columns and len(goldDn_day) > 0:
        tier_counts = goldDn_day["tier"].value_counts()
        for tier in ["S+⚡⚡", "S+⚡", "S+", "S"]:
            count = tier_counts.get(tier, 0)
            lines.append(f"   {tier}: {count}")
    
    # Top Filtered Signals
    lines.append("\n🏆 Top Filtered GoldDn Signals (by RSI)")
    lines.append("-" * 40)
    filtered = day[day["goldDn_filtered"]].sort_values("RSI")
    if len(filtered) > 0:
        for _, row in filtered.head(10).iterrows():
            lines.append(f"   {row['Stock_No']:>10} ({row['Country']}) "
                        f"RSI={row['RSI']:5.1f} Tier={row.get('tier', 'S'):>5} "
                        f"Close={row['Close']:8.2f} Blue7d={int(row.get('blueup_7d', 0))}")
    
    # 3-Tranche Prices
    lines.append("\n💹 3-Tranche 入場價 (Top 5)")
    lines.append("-" * 40)
    for _, row in filtered.head(5).iterrows():
        lines.append(f"   {row['Stock_No']:>10} T1={row['tranche1_price']:7.2f}(30%) "
                    f"T2={row['tranche2_price']:7.2f}(40%) T3={row['tranche3_price']:7.2f}(30%)")
    
    # Market Distribution
    lines.append("\n🌍 按市場分佈")
    lines.append("-" * 40)
    for country in ["HK", "US", "SZ", "SS", "ETF"]:
        c_data = day[day["Country"] == country]
        if len(c_data) > 0:
            gdn = int(c_data["is_GoldenPinDown"].sum())
            filtered_n = int(c_data["goldDn_filtered"].sum())
            lines.append(f"   {country:>6}: GoldDn={gdn} Filtered={filtered_n}")
    
    return "\n".join(lines)

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("📥 載入數據...")
    df = load_all_data()
    df = flag_signals(df)
    df = capitulation_filter(df)
    df = tier_enhancement(df)
    df = calc_tranche_prices(df)
    
    print("📊 生成儀表板...\n")
    dashboard = generate_dashboard(df)
    print(dashboard)
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"dashboard_{datetime.now().strftime('%Y-%m-%d')}.txt"
    output_path.write_text(dashboard, encoding="utf-8")
    print(f"\n💾 Dashboard 已保存至 {output_path}")
