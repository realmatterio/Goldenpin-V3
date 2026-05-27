#!/usr/bin/env python3
"""
Golden Pin Backtest — 回測引擎
Data source: workspace-stock-goldenpin
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import argparse

# ── Config ────────────────────────────────────────────────────────────────────
DATA_DIR = Path("../data/pretrain")
OUTPUT_DIR = Path(__file__).parent.parent / "output"

CAPITULATION_MAX_DROP_30D = 0.25
TIER_THRESHOLDS = {4: "S+⚡⚡", 3: "S+⚡", 2: "S+", 1: "S"}

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
                "WeakToStrong", "StrongToWeak", "GoldGateOnAlgo1", "GoldGateOnAlgo2"]:
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

def classify_indicators(df):
    df = df.copy()
    conditions = []
    # L17: GoldDn + Tier S+⚡⚡ + BlueUp 7d ≥ 3
    conditions.append(("L17", (df["Country"] == "HK") & df["goldDn_filtered"] & (df["tier"] == "S+⚡⚡") & (df["blueup_7d"] >= 3)))
    # L16: GoldDn + Tier S+⚡/S+⚡⚡ + BlueUp 7d ≥ 2
    conditions.append(("L16", (df["Country"] == "HK") & df["goldDn_filtered"] & (df["tier"].isin(["S+⚡", "S+⚡⚡"])) & (df["blueup_7d"] >= 2)))
    # L06: GoldDn + W2S
    conditions.append(("L06", (df["Country"] == "HK") & df["goldDn_filtered"] & df["is_WeakToStrong"]))
    # L04: GoldDn + GoldGate Algo1
    conditions.append(("L04", (df["Country"] == "HK") & df["goldDn_filtered"] & (df["GoldGateOnAlgo1"] == "Y")))
    # L03: GoldDn + RSI < 40
    conditions.append(("L03", (df["Country"] == "HK") & df["goldDn_filtered"] & (df["RSI"] < 40)))
    # S02: GoldUp + StrongToWeak + drop > 15%
    conditions.append(("S02", (df["Country"] == "HK") & df["is_GoldenPinUp"] & df["is_StrongToWeak"] & (df["drop_30d_pct"] > 0.15)))
    # S01: GoldUp + 無 BlueUp 7d
    conditions.append(("S01", (df["Country"] == "HK") & df["is_GoldenPinUp"] & (df["blueup_7d"] == 0)))
    # S11: GoldUp + drop > 10%
    conditions.append(("S11", (df["Country"] == "HK") & df["is_GoldenPinUp"] & (df["drop_30d_pct"] > 0.10)))
    conditions.append(("US01", (df["Country"] == "US") & df["goldDn_filtered"] & (df["tier"] == "S+⚡⚡")))
    conditions.append(("US02", (df["Country"] == "US") & df["goldDn_filtered"] & df["is_WeakToStrong"]))
    conditions.append(("US03", (df["Country"] == "US") & df["goldDn_filtered"] & (df["GoldGateOnAlgo1"] == "Y")))
    conditions.append(("US04", (df["Country"] == "US") & df["is_GoldenPinUp"] & df["is_StrongToWeak"]))
    conditions.append(("US05", (df["Country"] == "US") & df["is_GoldenPinUp"] & (df["blueup_7d"] == 0)))
    conditions.append(("US06", (df["Country"] == "US") & df["is_GoldenPinUp"] & (df["drop_30d_pct"] > 0.10)))
    for name, cond in conditions:
        df[f"ind_{name}"] = cond
    return df

# ── Backtest Engine ───────────────────────────────────────────────────────────
def backtest_indicator(df, indicator, hold_days=5):
    ind_col = f"ind_{indicator}"
    if ind_col not in df.columns:
        return pd.DataFrame()
    
    signals = df[df[ind_col]].copy()
    results = []
    
    for _, row in signals.iterrows():
        stock = row["Stock_No"]
        entry_date = row["Date"]
        entry_price = row["Close"]
        
        future = df[(df["Stock_No"] == stock) & (df["Date"] > entry_date)].sort_values("Date")
        if len(future) >= hold_days:
            exit_price = future.iloc[hold_days - 1]["Close"]
            pnl_pct = (exit_price - entry_price) / entry_price * 100
            future_prices = future.iloc[:hold_days]["Low"]
            max_dd = (future_prices.min() - entry_price) / entry_price * 100
            
            results.append({
                "stock": stock, "country": row["Country"], "indicator": indicator,
                "entry_date": entry_date, "entry_price": entry_price, "exit_price": exit_price,
                "pnl_pct": pnl_pct, "max_drawdown_pct": max_dd,
                "tier": row.get("tier", ""), "hold_days": hold_days,
            })
    
    return pd.DataFrame(results)

def backtest_all_indicators(df, hold_days=5):
    ind_cols = [c for c in df.columns if c.startswith("ind_")]
    all_results = []
    for col in ind_cols:
        name = col.replace("ind_", "")
        bt = backtest_indicator(df, name, hold_days=hold_days)
        if len(bt) > 0:
            all_results.append(bt)
    return pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()

# ── Report Generation ─────────────────────────────────────────────────────────
def generate_backtest_report(bt):
    if bt.empty:
        return "❌ 沒有回測數據"
    
    lines = []
    lines.append("=" * 70)
    lines.append("🔄 Golden Pin V3 回測報告")
    lines.append("=" * 70)
    
    # Overall Stats
    lines.append("\n📊 總體統計")
    lines.append("-" * 40)
    lines.append(f"   交易次數：{len(bt):,}")
    lines.append(f"   勝率：{(bt['pnl_pct'] > 0).mean():.1%}")
    lines.append(f"   平均回報：{bt['pnl_pct'].mean():+.2f}%")
    lines.append(f"   中位數回報：{bt['pnl_pct'].median():+.2f}%")
    lines.append(f"   最大回報：{bt['pnl_pct'].max():+.2f}%")
    lines.append(f"   最大虧損：{bt['pnl_pct'].min():+.2f}%")
    lines.append(f"   平均最大回撤：{bt['max_drawdown_pct'].mean():+.2f}%")
    
    # By Indicator
    lines.append("\n🎯 按 Indicator 分析")
    lines.append("-" * 40)
    for ind in sorted(bt["indicator"].unique()):
        ind_bt = bt[bt["indicator"] == ind]
        if len(ind_bt) > 0:
            wr = (ind_bt["pnl_pct"] > 0).mean()
            avg = ind_bt["pnl_pct"].mean()
            lines.append(f"   {ind:>4}: n={len(ind_bt):>5} 勝率={wr:.1%} 平均={avg:>+6.2f}% 最大={ind_bt['pnl_pct'].max():>+7.2f}%")
    
    # By Tier
    lines.append("\n⚡ 按 Tier 分析")
    lines.append("-" * 40)
    for tier in ["S+⚡⚡", "S+⚡", "S+", "S"]:
        tier_bt = bt[bt["tier"] == tier]
        if len(tier_bt) > 0:
            wr = (tier_bt["pnl_pct"] > 0).mean()
            avg = tier_bt["pnl_pct"].mean()
            lines.append(f"   {tier:>5}: n={len(tier_bt):>5} 勝率={wr:.1%} 平均={avg:>+6.2f}%")
    
    # By Market
    lines.append("\n🌍 按市場分析")
    lines.append("-" * 40)
    for country in sorted(bt["country"].unique()):
        c_bt = bt[bt["country"] == country]
        if len(c_bt) > 0:
            wr = (c_bt["pnl_pct"] > 0).mean()
            avg = c_bt["pnl_pct"].mean()
            lines.append(f"   {country:>6}: n={len(c_bt):>5} 勝率={wr:.1%} 平均={avg:>+6.2f}%")
    
    return "\n".join(lines)

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Golden Pin V3 Backtest")
    parser.add_argument("--hold-days", type=int, default=5, help="持有天數 (預設：5)")
    args = parser.parse_args()
    
    print("📥 載入數據...")
    df = load_all_data()
    
    print("🔧 處理信號...")
    df = flag_signals(df)
    df = capitulation_filter(df)
    df = tier_enhancement(df)
    df = classify_indicators(df)
    
    print(f"🔄 回測所有 Indicators ({args.hold_days}日持有)...")
    bt = backtest_all_indicators(df, hold_days=args.hold_days)
    
    print("📊 生成報告...\n")
    report = generate_backtest_report(bt)
    print(report)
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    bt.to_csv(OUTPUT_DIR / f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", index=False)
    report_path = OUTPUT_DIR / f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n💾 回測結果已保存至 {OUTPUT_DIR}/")
