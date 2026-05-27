#!/usr/bin/env python3
"""
V3 (舊) vs V3.1 (新) 14 Indicators 回測對比
用 Google Drive 原始 CSV 數據驗證勝率提升
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path("/Users/ttse/.openclaw/workspace-stock-goldenpin/data/Golden Pin Stockbot - OpenClaw")
OUTPUT_DIR = Path(__file__).parent.parent / "output"

# ══════════════════════════════════════════════════════════════════════════════
# 1. DATA LOADING + PROCESSING
# ══════════════════════════════════════════════════════════════════════════════

def load_and_process():
    dfs = []
    for f in sorted(DATA_DIR.glob("StockDailyPins*.csv*")):
        try:
            df = pd.read_csv(f)
            if "GoldGateOnAlgo1" not in df.columns:
                df["GoldGateOnAlgo1"] = "N"
                df["GoldGateOnAlgo2"] = "N"
            dfs.append(df)
        except Exception as e:
            print(f"   ⚠️ {f.name}: {e}")
    
    df = pd.concat(dfs, ignore_index=True)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values(["Stock_No", "Date"]).reset_index(drop=True)
    df = df[(df["Close"] > 0) & (df["Volume"] > 0)].copy()
    
    # Flag signals
    for col in ["GoldenPinDown", "GoldenPinUp", "BluePinUp", "BluePinDown",
                "WeakToStrong", "StrongToWeak", "GreyPinDown",
                "GoldGateOnAlgo1", "GoldGateOnAlgo2"]:
        if col in df.columns:
            df[f"is_{col}"] = df[col] == "Y"
    
    # Capitulation Filter
    df["close_30d_ago"] = df.groupby("Stock_No")["Close"].shift(30)
    df["return_30d"] = (df["Close"] - df["close_30d_ago"]) / df["close_30d_ago"]
    df["drop_30d_pct"] = -df["return_30d"]
    df["blueup_7d"] = df.groupby("Stock_No")["is_BluePinUp"].transform(
        lambda x: x.rolling(7, min_periods=1).sum()).astype(int)
    df["w2s_7d"] = df.groupby("Stock_No")["is_WeakToStrong"].transform(
        lambda x: x.rolling(7, min_periods=1).sum()).astype(int)
    df["has_institutional_support"] = (df["blueup_7d"] > 0) | (df["w2s_7d"] > 0)
    df["drop_under_25pct"] = df["drop_30d_pct"] < 0.25
    df["goldDn_filtered"] = df["is_GoldenPinDown"] & df["has_institutional_support"] & df["drop_under_25pct"]
    
    # Tier
    df["goldDn_30d_count"] = df.groupby("Stock_No")["is_GoldenPinDown"].transform(
        lambda x: x.rolling(30, min_periods=1).sum()).astype(int)
    tier_map = {4: "S+⚡⚡", 3: "S+⚡", 2: "S+", 1: "S"}
    df["tier"] = df["goldDn_30d_count"].apply(
        lambda x: tier_map.get(x, "S+⚡⚡") if x >= 1 else None)
    df.loc[~df["is_GoldenPinDown"], "tier"] = None
    
    return df

# ══════════════════════════════════════════════════════════════════════════════
# 2. V3 舊定義 vs V3.1 新定義
# ══════════════════════════════════════════════════════════════════════════════

V3_OLD = {
    "L17": {"cond": lambda d: (d["Country"]=="HK") & d["goldDn_filtered"] & (d["tier"]=="S+⚡⚡") & (d["blueup_7d"]>=3), "dir": "LONG",
            "def": "GoldDn+Cap+Tier⚡⚡+Blue≥3"},
    "L16": {"cond": lambda d: (d["Country"]=="HK") & d["goldDn_filtered"] & (d["tier"].isin(["S+⚡","S+⚡⚡"])) & (d["blueup_7d"]>=2), "dir": "LONG",
            "def": "GoldDn+Cap+Tier⚡/⚡⚡+Blue≥2"},
    "L06": {"cond": lambda d: (d["Country"]=="HK") & d["goldDn_filtered"] & d["is_WeakToStrong"], "dir": "LONG",
            "def": "GoldDn+Cap+W2S"},
    "L04": {"cond": lambda d: (d["Country"]=="HK") & d["goldDn_filtered"] & (d["GoldGateOnAlgo1"]=="Y"), "dir": "LONG",
            "def": "GoldDn+Cap+GoldGate1"},
    "L03": {"cond": lambda d: (d["Country"]=="HK") & d["goldDn_filtered"] & (d["RSI"]<40), "dir": "LONG",
            "def": "GoldDn+Cap+RSI<40"},
    "S02": {"cond": lambda d: (d["Country"]=="HK") & d["is_GoldenPinUp"] & d["is_StrongToWeak"] & (d["drop_30d_pct"]>0.15), "dir": "SHO",
            "def": "GoldUp+S2W+Drop>15%"},
    "S01": {"cond": lambda d: (d["Country"]=="HK") & d["is_GoldenPinUp"] & (d["blueup_7d"]==0), "dir": "SHO",
            "def": "GoldUp+Blue=0"},
    "S11": {"cond": lambda d: (d["Country"]=="HK") & d["is_GoldenPinUp"] & (d["drop_30d_pct"]>0.10), "dir": "SHO",
            "def": "GoldUp+Drop>10%"},
    "US01": {"cond": lambda d: (d["Country"]=="US") & d["goldDn_filtered"] & (d["tier"]=="S+⚡⚡"), "dir": "LONG",
             "def": "US GoldDn+Cap+Tier⚡⚡"},
    "US02": {"cond": lambda d: (d["Country"]=="US") & d["goldDn_filtered"] & d["is_WeakToStrong"], "dir": "LONG",
             "def": "US GoldDn+Cap+W2S"},
    "US03": {"cond": lambda d: (d["Country"]=="US") & d["goldDn_filtered"] & (d["GoldGateOnAlgo1"]=="Y"), "dir": "LONG",
             "def": "US GoldDn+Cap+GoldGate1"},
    "US04": {"cond": lambda d: (d["Country"]=="US") & d["is_GoldenPinUp"] & d["is_StrongToWeak"], "dir": "SHO",
             "def": "US GoldUp+S2W"},
    "US05": {"cond": lambda d: (d["Country"]=="US") & d["is_GoldenPinUp"] & (d["blueup_7d"]==0), "dir": "SHO",
             "def": "US GoldUp+Blue=0"},
    "US06": {"cond": lambda d: (d["Country"]=="US") & d["is_GoldenPinUp"] & (d["drop_30d_pct"]>0.10), "dir": "SHO",
             "def": "US GoldUp+Drop>10%"},
}

V31_NEW = {
    "L17": {"cond": lambda d: (d["Country"]=="HK") & d["goldDn_filtered"] & (d["tier"]=="S+⚡⚡") & (d["blueup_7d"]>=1) & (d["RSI"]<50), "dir": "LONG",
            "def": "GoldDn+Cap+Tier⚡⚡+Blue≥1+RSI<50"},
    "L16": {"cond": lambda d: (d["Country"]=="HK") & d["goldDn_filtered"] & (d["tier"].isin(["S+","S+⚡","S+⚡⚡"])) & (d["blueup_7d"]>=1), "dir": "LONG",
            "def": "GoldDn+Cap+Tier≥S++Blue≥1"},
    "L06": {"cond": lambda d: (d["Country"]=="HK") & d["is_GoldenPinDown"] & d["is_WeakToStrong"], "dir": "LONG",
            "def": "GoldDn+W2S (無Cap)"},
    "L04": {"cond": lambda d: (d["Country"]=="HK") & d["is_GoldenPinDown"] & (d["GoldGateOnAlgo1"]=="Y"), "dir": "LONG",
            "def": "GoldDn+GoldGate1 (無Cap)"},
    "L03": {"cond": lambda d: (d["Country"]=="HK") & d["goldDn_filtered"] & (d["RSI"]<45), "dir": "LONG",
            "def": "GoldDn+Cap+RSI<45"},
    "S02": {"cond": lambda d: (d["Country"]=="HK") & d["is_GoldenPinUp"] & d["is_StrongToWeak"] & (d["drop_30d_pct"]>0.10) & (d["RSI"]>60), "dir": "SHO",
            "def": "GoldUp+S2W+Drop>10%+RSI>60"},
    "S01": {"cond": lambda d: (d["Country"]=="HK") & d["is_GoldenPinUp"] & (d["blueup_7d"]==0) & (d["RSI"]>60), "dir": "SHO",
            "def": "GoldUp+Blue=0+RSI>60"},
    "S11": {"cond": lambda d: (d["Country"]=="HK") & d["is_GoldenPinUp"] & (d["drop_30d_pct"]>0.10) & (d["RSI"]>55), "dir": "SHO",
            "def": "GoldUp+Drop>10%+RSI>55"},
    "US01": {"cond": lambda d: (d["Country"]=="US") & d["is_GoldenPinDown"] & (d["tier"]=="S+⚡⚡"), "dir": "LONG",
             "def": "US GoldDn+Tier⚡⚡ (無Cap)"},
    "US02": {"cond": lambda d: (d["Country"]=="US") & d["is_GoldenPinDown"] & d["is_WeakToStrong"], "dir": "LONG",
             "def": "US GoldDn+W2S (無Cap)"},
    "US03": {"cond": lambda d: (d["Country"]=="US") & d["is_GoldenPinDown"] & (d["GoldGateOnAlgo1"]=="Y"), "dir": "LONG",
             "def": "US GoldDn+GoldGate1 (無Cap)"},
    "US04": {"cond": lambda d: (d["Country"]=="US") & d["is_GoldenPinUp"] & d["is_StrongToWeak"] & (d["RSI"]>55), "dir": "SHO",
             "def": "US GoldUp+S2W+RSI>55"},
    "US05": {"cond": lambda d: (d["Country"]=="US") & d["is_GoldenPinUp"] & (d["blueup_7d"]==0), "dir": "SHO",
             "def": "US GoldUp+Blue=0"},
    "US06": {"cond": lambda d: (d["Country"]=="US") & d["is_GoldenPinUp"] & (d["RSI"]>60), "dir": "SHO",
             "def": "US GoldUp+RSI>60"},
}

# ══════════════════════════════════════════════════════════════════════════════
# 3. BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def backtest(df, mask, direction, hold_days=5):
    signals = df[mask].copy()
    results = []
    for _, row in signals.iterrows():
        stock = row["Stock_No"]
        entry_date = row["Date"]
        entry_price = row["Close"]
        if pd.isna(entry_price) or entry_price <= 0:
            continue
        future = df[(df["Stock_No"] == stock) & (df["Date"] > entry_date)].sort_values("Date")
        if len(future) >= hold_days:
            exit_price = future.iloc[hold_days - 1]["Close"]
            pnl = (exit_price - entry_price) / entry_price * 100
            if direction == "SHO":
                pnl = -pnl
            results.append(pnl)
    if not results:
        return None
    r = np.array(results)
    return {
        "n": len(r),
        "win_rate": (r > 0).mean(),
        "avg_pnl": r.mean(),
        "median_pnl": np.median(r),
        "max_win": r.max(),
        "max_loss": r.min(),
    }

# ══════════════════════════════════════════════════════════════════════════════
# 4. COMPARISON
# ══════════════════════════════════════════════════════════════════════════════

def compare_versions(df, hold_days=5):
    print(f"\n{'='*80}")
    print(f"📊 V3 (舊) vs V3.1 (新) 14 Indicators 回測對比 — {hold_days} 日持有")
    print(f"{'='*80}")
    
    indicator_names = ["L17","L16","L06","L04","L03","S02","S01","S11",
                       "US01","US02","US03","US04","US05","US06"]
    
    print(f"\n   {'Ind':<6} {'方向':<5} │ {'V3 舊':>18} │ {'V3.1 新':>18} │ {'變化':>12}")
    print(f"   {'─'*6} {'─'*5} │ {'─'*18} │ {'─'*18} │ {'─'*12}")
    
    total_old_wr = []
    total_new_wr = []
    total_old_pnl = []
    total_new_pnl = []
    
    for name in indicator_names:
        old = V3_OLD[name]
        new = V31_NEW[name]
        direction = old["dir"]
        
        old_mask = old["cond"](df)
        new_mask = new["cond"](df)
        
        old_n = int(old_mask.sum())
        new_n = int(new_mask.sum())
        
        old_bt = backtest(df, old_mask, direction, hold_days)
        new_bt = backtest(df, new_mask, direction, hold_days)
        
        # Format
        if old_bt:
            old_str = f"n={old_bt['n']:>4} WR={old_bt['win_rate']:.1%} PnL={old_bt['avg_pnl']:+.1f}%"
            total_old_wr.append(old_bt["win_rate"])
            total_old_pnl.append(old_bt["avg_pnl"])
        else:
            old_str = f"n=   0     N/A      N/A"
        
        if new_bt:
            new_str = f"n={new_bt['n']:>4} WR={new_bt['win_rate']:.1%} PnL={new_bt['avg_pnl']:+.1f}%"
            total_new_wr.append(new_bt["win_rate"])
            total_new_pnl.append(new_bt["avg_pnl"])
        else:
            new_str = f"n=   0     N/A      N/A"
        
        # Change
        if old_bt and new_bt:
            wr_change = new_bt["win_rate"] - old_bt["win_rate"]
            pnl_change = new_bt["avg_pnl"] - old_bt["avg_pnl"]
            change_str = f"WR{wr_change:+.1%} PnL{pnl_change:+.1f}%"
        elif new_bt and not old_bt:
            change_str = "🆕 新增數據"
        else:
            change_str = "—"
        
        print(f"   {name:<6} {direction:<5} │ {old_str} │ {new_str} │ {change_str}")
    
    # Summary
    print(f"\n   {'='*80}")
    print(f"   📊 總結對比")
    print(f"   {'='*80}")
    
    if total_old_wr and total_new_wr:
        avg_old_wr = np.mean(total_old_wr)
        avg_new_wr = np.mean(total_new_wr)
        avg_old_pnl = np.mean(total_old_pnl)
        avg_new_pnl = np.mean(total_new_pnl)
        
        print(f"\n   │          │ V3 舊      │ V3.1 新    │ 變化       │")
        print(f"   │──────────│────────────│────────────│────────────│")
        print(f"   │ 平均勝率 │ {avg_old_wr:>8.1%}   │ {avg_new_wr:>8.1%}   │ {avg_new_wr-avg_old_wr:>+8.1%}   │")
        print(f"   │ 平均PnL  │ {avg_old_pnl:>+7.2f}%  │ {avg_new_pnl:>+7.2f}%  │ {avg_new_pnl-avg_old_pnl:>+7.2f}%  │")
    
    return total_old_wr, total_new_wr, total_old_pnl, total_new_pnl

def multi_hold_comparison(df):
    """多個持有期對比"""
    print(f"\n{'='*80}")
    print(f"📈 多持有期對比: V3 舊 vs V3.1 新")
    print(f"{'='*80}")
    
    long_names = ["L17","L16","L06","L04","L03","US01","US02","US03"]
    sho_names = ["S02","S01","S11","US04","US05","US06"]
    
    print(f"\n   📊 LONG Indicators 平均勝率")
    print(f"   {'持有期':>6} │ {'V3 舊':>8} │ {'V3.1 新':>8} │ {'Δ勝率':>8} │ {'V3 PnL':>9} │ {'V3.1 PnL':>9} │ {'ΔPnL':>8}")
    print(f"   {'─'*80}")
    
    for hold in [3, 5, 7, 10, 14, 20]:
        old_wrs, new_wrs = [], []
        old_pnls, new_pnls = [], []
        
        for name in long_names:
            old_bt = backtest(df, V3_OLD[name]["cond"](df), "LONG", hold)
            new_bt = backtest(df, V31_NEW[name]["cond"](df), "LONG", hold)
            if old_bt and old_bt["n"] >= 3:
                old_wrs.append(old_bt["win_rate"])
                old_pnls.append(old_bt["avg_pnl"])
            if new_bt and new_bt["n"] >= 3:
                new_wrs.append(new_bt["win_rate"])
                new_pnls.append(new_bt["avg_pnl"])
        
        avg_old_wr = np.mean(old_wrs) if old_wrs else 0
        avg_new_wr = np.mean(new_wrs) if new_wrs else 0
        avg_old_pnl = np.mean(old_pnls) if old_pnls else 0
        avg_new_pnl = np.mean(new_pnls) if new_pnls else 0
        
        wr_d = avg_new_wr - avg_old_wr
        pnl_d = avg_new_pnl - avg_old_pnl
        
        print(f"   {hold:>4}日 │ {avg_old_wr:>7.1%} │ {avg_new_wr:>7.1%} │ {wr_d:>+7.1%} │ {avg_old_pnl:>+8.2f}% │ {avg_new_pnl:>+8.2f}% │ {pnl_d:>+7.2f}%")
    
    print(f"\n   📊 SHO Indicators 平均勝率")
    print(f"   {'持有期':>6} │ {'V3 舊':>8} │ {'V3.1 新':>8} │ {'Δ勝率':>8}")
    print(f"   {'─'*50}")
    
    for hold in [3, 5, 7, 10, 14, 20]:
        old_wrs, new_wrs = [], []
        for name in sho_names:
            old_bt = backtest(df, V3_OLD[name]["cond"](df), "SHO", hold)
            new_bt = backtest(df, V31_NEW[name]["cond"](df), "SHO", hold)
            if old_bt and old_bt["n"] >= 3:
                old_wrs.append(old_bt["win_rate"])
            if new_bt and new_bt["n"] >= 3:
                new_wrs.append(new_bt["win_rate"])
        
        avg_old = np.mean(old_wrs) if old_wrs else 0
        avg_new = np.mean(new_wrs) if new_wrs else 0
        print(f"   {hold:>4}日 │ {avg_old:>7.1%} │ {avg_new:>7.1%} │ {avg_new-avg_old:>+7.1%}")

# ══════════════════════════════════════════════════════════════════════════════
# 5. DETAILED PER-INDICATOR
# ══════════════════════════════════════════════════════════════════════════════

def detailed_comparison(df):
    """每個 Indicator 嘅詳細新舊定義對比"""
    print(f"\n{'='*80}")
    print(f"🔍 每個 Indicator 新舊定義詳細對比 (5 日持有)")
    print(f"{'='*80}")
    
    indicator_names = ["L17","L16","L06","L04","L03","S02","S01","S11",
                       "US01","US02","US03","US04","US05","US06"]
    
    for name in indicator_names:
        old = V3_OLD[name]
        new = V31_NEW[name]
        direction = old["dir"]
        
        print(f"\n   🏷️  {name} ({direction})")
        print(f"   {'─'*60}")
        print(f"   V3 舊:  {old['def']}")
        print(f"   V3.1 新: {new['def']}")
        
        old_bt = backtest(df, old["cond"](df), direction, 5)
        new_bt = backtest(df, new["cond"](df), direction, 5)
        
        if old_bt:
            print(f"   V3  結果: n={old_bt['n']} 勝率={old_bt['win_rate']:.1%} PnL={old_bt['avg_pnl']:+.2f}% 中位={old_bt['median_pnl']:+.2f}%")
        else:
            print(f"   V3  結果: 無數據")
        
        if new_bt:
            print(f"   V3.1結果: n={new_bt['n']} 勝率={new_bt['win_rate']:.1%} PnL={new_bt['avg_pnl']:+.2f}% 中位={new_bt['median_pnl']:+.2f}%")
        else:
            print(f"   V3.1結果: 無數據")
        
        if old_bt and new_bt:
            wr_d = new_bt["win_rate"] - old_bt["win_rate"]
            pnl_d = new_bt["avg_pnl"] - old_bt["avg_pnl"]
            emoji = "✅" if wr_d > 0 or pnl_d > 0 else "⚠️"
            print(f"   {emoji} 變化: 勝率{wr_d:+.1%} PnL{pnl_d:+.2f}%")

# ══════════════════════════════════════════════════════════════════════════════
# 6. MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🦞 黃金針 V3 vs V3.1 — 14 Indicators 回測對比")
    print(f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"數據源：Google Drive CSV (2024-01 至 2026-05)")
    
    print(f"\n📥 載入並處理數據...")
    df = load_and_process()
    print(f"   總行數：{len(df):,} | 股票數：{df['Stock_No'].nunique()}")
    print(f"   日期範圍：{df['Date'].min().date()} 至 {df['Date'].max().date()}")
    print(f"   GoldDn 原始：{int(df['is_GoldenPinDown'].sum()):,} | Filtered：{int(df['goldDn_filtered'].sum()):,}")
    print(f"   GoldUp：{int(df['is_GoldenPinUp'].sum()):,}")
    
    # 1. 5 日持有對比
    compare_versions(df, hold_days=5)
    
    # 2. 多持有期對比
    multi_hold_comparison(df)
    
    # 3. 詳細對比
    detailed_comparison(df)
    
    # 4. 總結
    print(f"\n{'='*80}")
    print(f"📝 V3.1 修正總結")
    print(f"{'='*80}")
    print(f"""
    修正項目：
    ┌────────┬─────────────────────────────────────────────┐
    │ L17    │ Blue≥3→Blue≥1, 加 RSI<50                   │
    │ L16    │ Blue≥2→Blue≥1, Tier 擴展至 S+              │
    │ L03    │ RSI<40→RSI<45 (逆向工程證實勝率更高)          │
    │ L06    │ 移除 Capitulation Filter (W2S=反轉信號)      │
    │ L04    │ 移除 Capitulation Filter (GoldGate=獨立算法)  │
    │ S02    │ Drop>15%→10%, 加 RSI>60                     │
    │ S01    │ 加 RSI>60 (提升選股精度)                      │
    │ S11    │ 加 RSI>55 (避免低位假信號)                    │
    │ US01-3 │ 移除 Capitulation Filter (美股基礎池太少)     │
    │ US04   │ 加 RSI>55                                   │
    │ US06   │ Drop>10%→RSI>60                             │
    └────────┴─────────────────────────────────────────────┘
    """)
    
    print(f"💾 回測完成")