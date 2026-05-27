#!/usr/bin/env python3
"""
V3.2 最終優化 — 平衡勝率 vs 樣本數
目標：勝率≥65% + 樣本≥20
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path("/Users/ttse/.openclaw/workspace-stock-goldenpin/data/Golden Pin Stockbot - OpenClaw")
TARGET_WR = 0.65
MIN_N = 20

def load_data():
    dfs = []
    for f in sorted(DATA_DIR.glob("StockDailyPins*.csv*")):
        try:
            df = pd.read_csv(f)
            if "GoldGateOnAlgo1" not in df.columns:
                df["GoldGateOnAlgo1"] = "N"
                df["GoldGateOnAlgo2"] = "N"
            dfs.append(df)
        except:
            pass
    df = pd.concat(dfs, ignore_index=True)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values(["Stock_No", "Date"]).reset_index(drop=True)
    df = df[(df["Close"] > 0) & (df["Volume"] > 0)].copy()
    
    for col in ["GoldenPinDown","GoldenPinUp","BluePinUp","BluePinDown",
                "WeakToStrong","StrongToWeak","GreyPinDown","GoldGateOnAlgo1","GoldGateOnAlgo2"]:
        if col in df.columns:
            df[f"is_{col}"] = df[col] == "Y"
    
    df["close_30d_ago"] = df.groupby("Stock_No")["Close"].shift(30)
    df["drop_30d_pct"] = -(df["Close"] - df["close_30d_ago"]) / df["close_30d_ago"]
    
    for n in [3,5,7,10,14,30]:
        df[f"blueup_{n}d"] = df.groupby("Stock_No")["is_BluePinUp"].transform(
            lambda x: x.rolling(n, min_periods=1).sum()).astype(int)
        df[f"w2s_{n}d"] = df.groupby("Stock_No")["is_WeakToStrong"].transform(
            lambda x: x.rolling(n, min_periods=1).sum()).astype(int)
        df[f"goldDn_{n}d"] = df.groupby("Stock_No")["is_GoldenPinDown"].transform(
            lambda x: x.rolling(n, min_periods=1).sum()).astype(int)
    
    df["has_inst_support"] = (df["blueup_7d"] > 0) | (df["w2s_7d"] > 0)
    df["goldDn_filtered"] = df["is_GoldenPinDown"] & df["has_inst_support"] & (df["drop_30d_pct"] < 0.25)
    df["goldDn_filt_30d_count"] = df.groupby("Stock_No")["goldDn_filtered"].transform(
        lambda x: x.rolling(30, min_periods=1).sum()).astype(int)
    df["goldDn_30d_count"] = df.groupby("Stock_No")["is_GoldenPinDown"].transform(
        lambda x: x.rolling(30, min_periods=1).sum()).astype(int)
    tier_map = {4: "S+⚡⚡", 3: "S+⚡", 2: "S+", 1: "S"}
    df["tier"] = df["goldDn_30d_count"].apply(lambda x: tier_map.get(x, "S+⚡⚡") if x >= 1 else None)
    df.loc[~df["is_GoldenPinDown"], "tier"] = None
    df["no_recent_gd"] = df["NoRecentGdPinsDw"].str.strip() != ""
    df["drop_10pct"] = df["drop_30d_pct"] > 0.10
    df["drop_15pct"] = df["drop_30d_pct"] > 0.15
    
    # 向量化回測
    for hold in [5, 7, 10, 14]:
        df[f"close_{hold}d_future"] = df.groupby("Stock_No")["Close"].shift(-hold)
        df[f"pnl_{hold}d_long"] = (df[f"close_{hold}d_future"] - df["Close"]) / df["Close"] * 100
        df[f"pnl_{hold}d_sho"] = -df[f"pnl_{hold}d_long"]
    
    return df

def vbt(df, mask, direction, hold=5, min_n=MIN_N):
    d = df[mask & df[f"pnl_{hold}d_long"].notna()].copy()
    if len(d) < min_n:
        return None
    pnl = d[f"pnl_{hold}d_long"] if direction == "LONG" else d[f"pnl_{hold}d_sho"]
    return {"n": len(d), "win_rate": (pnl > 0).mean(), "avg_pnl": pnl.mean(), "median_pnl": pnl.median()}

def exhaustive_search(df):
    print(f"\n{'='*80}")
    print(f"🔬 V3.2 窮舉搜尋 — 目標勝率≥{TARGET_WR:.0%} 樣本≥{MIN_N}")
    print(f"{'='*80}")
    
    # ═══ HK LONG ═══
    print(f"\n   🟡 HK LONG")
    base = (df["Country"] == "HK") & df["is_GoldenPinDown"]
    
    # 定義所有要測試嘅組合
    hk_long_combos = [
        # (name, conditions_list)
        ("Cap+RSI<45+W2S7d≥1", [df["goldDn_filtered"], df["RSI"] < 45, df["w2s_7d"] >= 1]),
        ("Cap+RSI<45+W2S14d≥1", [df["goldDn_filtered"], df["RSI"] < 45, df["w2s_14d"] >= 1]),
        ("Cap+RSI<40+W2S7d≥1", [df["goldDn_filtered"], df["RSI"] < 40, df["w2s_7d"] >= 1]),
        ("Cap+RSI<35+W2S7d≥1", [df["goldDn_filtered"], df["RSI"] < 35, df["w2s_7d"] >= 1]),
        ("Cap+RSI<45+Blue14d≥2", [df["goldDn_filtered"], df["RSI"] < 45, df["blueup_14d"] >= 2]),
        ("Cap+RSI<45+Blue14d≥3", [df["goldDn_filtered"], df["RSI"] < 45, df["blueup_14d"] >= 3]),
        ("Cap+RSI<40+Blue14d≥2", [df["goldDn_filtered"], df["RSI"] < 40, df["blueup_14d"] >= 2]),
        ("Cap+RSI<35+Blue14d≥2", [df["goldDn_filtered"], df["RSI"] < 35, df["blueup_14d"] >= 2]),
        ("Cap+RSI<45+GoldDn_filt30d≥3", [df["goldDn_filtered"], df["RSI"] < 45, df["goldDn_filt_30d_count"] >= 3]),
        ("Cap+RSI<45+GoldDn_filt30d≥4", [df["goldDn_filtered"], df["RSI"] < 45, df["goldDn_filt_30d_count"] >= 4]),
        ("Cap+RSI<40+GoldDn_filt30d≥3", [df["goldDn_filtered"], df["RSI"] < 40, df["goldDn_filt_30d_count"] >= 3]),
        ("Cap+RSI<35+GoldDn_filt30d≥3", [df["goldDn_filtered"], df["RSI"] < 35, df["goldDn_filt_30d_count"] >= 3]),
        ("Cap+Tier≥S++RSI<45", [df["goldDn_filtered"], df["tier"].isin(["S+","S+⚡","S+⚡⚡"]), df["RSI"] < 45]),
        ("Cap+Tier≥S+⚡+RSI<45", [df["goldDn_filtered"], df["tier"].isin(["S+⚡","S+⚡⚡"]), df["RSI"] < 45]),
        ("Cap+Tier=S+⚡⚡+RSI<45", [df["goldDn_filtered"], df["tier"] == "S+⚡⚡", df["RSI"] < 45]),
        ("Cap+Tier=S+⚡⚡+RSI<50", [df["goldDn_filtered"], df["tier"] == "S+⚡⚡", df["RSI"] < 50]),
        # 4 條件
        ("Cap+RSI<45+W2S7d≥1+Blue14d≥2", [df["goldDn_filtered"], df["RSI"] < 45, df["w2s_7d"] >= 1, df["blueup_14d"] >= 2]),
        ("Cap+RSI<45+W2S7d≥1+GoldDn_filt30d≥3", [df["goldDn_filtered"], df["RSI"] < 45, df["w2s_7d"] >= 1, df["goldDn_filt_30d_count"] >= 3]),
        ("Cap+RSI<45+W2S7d≥1+Tier≥S+", [df["goldDn_filtered"], df["RSI"] < 45, df["w2s_7d"] >= 1, df["tier"].isin(["S+","S+⚡","S+⚡⚡"])]),
        ("Cap+RSI<40+W2S7d≥1+Blue14d≥2", [df["goldDn_filtered"], df["RSI"] < 40, df["w2s_7d"] >= 1, df["blueup_14d"] >= 2]),
        ("Cap+RSI<45+Blue14d≥2+Tier≥S+", [df["goldDn_filtered"], df["RSI"] < 45, df["blueup_14d"] >= 2, df["tier"].isin(["S+","S+⚡","S+⚡⚡"])]),
        ("Cap+RSI<45+Blue14d≥2+GoldDn_filt30d≥3", [df["goldDn_filtered"], df["RSI"] < 45, df["blueup_14d"] >= 2, df["goldDn_filt_30d_count"] >= 3]),
        # 5 條件
        ("Cap+RSI<45+W2S7d≥1+Blue14d≥2+Tier≥S+", [df["goldDn_filtered"], df["RSI"] < 45, df["w2s_7d"] >= 1, df["blueup_14d"] >= 2, df["tier"].isin(["S+","S+⚡","S+⚡⚡"])]),
        ("Cap+RSI<40+W2S7d≥1+Blue14d≥2+Tier≥S+", [df["goldDn_filtered"], df["RSI"] < 40, df["w2s_7d"] >= 1, df["blueup_14d"] >= 2, df["tier"].isin(["S+","S+⚡","S+⚡⚡"])]),
        # 無 Cap 版本
        ("GoldDn+W2S", [df["is_GoldenPinDown"], df["is_WeakToStrong"]]),
        ("GoldDn+GoldGate1", [df["is_GoldenPinDown"], df["GoldGateOnAlgo1"] == "Y"]),
        # 更多持有期
    ]
    
    print(f"\n   {'組合':<50} {'5日':>15} {'7日':>15} {'10日':>15} {'14日':>15}")
    print(f"   {'-'*80}")
    
    best_long = []
    for name, conds in hk_long_combos:
        mask = base.copy()
        for c in conds:
            mask = mask & c
        
        row = f"   {name:<50}"
        for hold in [5, 7, 10, 14]:
            bt = vbt(df, mask, "LONG", hold, min_n=10)
            if bt:
                flag = "🔥" if bt["win_rate"] >= TARGET_WR else ""
                row += f" {bt['n']:>3}WR={bt['win_rate']:.0%}{flag}"
            else:
                row += f"    N/A    "
        print(row)
        
        bt5 = vbt(df, mask, "LONG", 5, min_n=10)
        if bt5:
            best_long.append((name, bt5, mask))
    
    # ═══ HK SHO ═══
    print(f"\n   🔴 HK SHO")
    base_s = (df["Country"] == "HK") & df["is_GoldenPinUp"]
    
    hk_sho_combos = [
        ("Blue7d=0+RSI>60", [df["blueup_7d"] == 0, df["RSI"] > 60]),
        ("Blue7d=0+RSI>65", [df["blueup_7d"] == 0, df["RSI"] > 65]),
        ("Blue7d=0+RSI>70", [df["blueup_7d"] == 0, df["RSI"] > 70]),
        ("Blue14d=0+RSI>60", [df["blueup_14d"] == 0, df["RSI"] > 60]),
        ("Blue14d=0+RSI>65", [df["blueup_14d"] == 0, df["RSI"] > 65]),
        ("Blue14d=0+RSI>70", [df["blueup_14d"] == 0, df["RSI"] > 70]),
        ("Blue14d≤1+RSI>60", [df["blueup_14d"] <= 1, df["RSI"] > 60]),
        ("Blue14d≤1+RSI>65", [df["blueup_14d"] <= 1, df["RSI"] > 65]),
        ("Blue30d≤1+RSI>60", [df["blueup_30d"] <= 1, df["RSI"] > 60]),
        ("Blue30d≤1+RSI>65", [df["blueup_30d"] <= 1, df["RSI"] > 65]),
        ("Blue30d≤1+RSI>60+Drop>15%", [df["blueup_30d"] <= 1, df["RSI"] > 60, df["drop_15pct"]]),
        ("Blue14d=0+RSI>60+Drop>10%", [df["blueup_14d"] == 0, df["RSI"] > 60, df["drop_10pct"]]),
        ("Blue7d=0+RSI>60+Drop>10%", [df["blueup_7d"] == 0, df["RSI"] > 60, df["drop_10pct"]]),
        ("Blue7d=0+RSI>65+Drop>10%", [df["blueup_7d"] == 0, df["RSI"] > 65, df["drop_10pct"]]),
        ("Blue7d=0+S2W+RSI>60", [df["blueup_7d"] == 0, df["is_StrongToWeak"], df["RSI"] > 60]),
        ("Blue14d=0+S2W+RSI>60", [df["blueup_14d"] == 0, df["is_StrongToWeak"], df["RSI"] > 60]),
    ]
    
    print(f"\n   {'組合':<45} {'5日':>15} {'7日':>15} {'10日':>15}")
    print(f"   {'-'*75}")
    
    best_sho = []
    for name, conds in hk_sho_combos:
        mask = base_s.copy()
        for c in conds:
            mask = mask & c
        
        row = f"   {name:<45}"
        for hold in [5, 7, 10]:
            bt = vbt(df, mask, "SHO", hold, min_n=10)
            if bt:
                flag = "🔥" if bt["win_rate"] >= TARGET_WR else ""
                row += f" {bt['n']:>3}WR={bt['win_rate']:.0%}{flag}"
            else:
                row += f"    N/A    "
        print(row)
        
        bt5 = vbt(df, mask, "SHO", 5, min_n=10)
        if bt5:
            best_sho.append((name, bt5, mask))
    
    # ═══ US ═══
    print(f"\n   🌎 US LONG")
    base_us_l = (df["Country"] == "US") & df["is_GoldenPinDown"]
    us_long_combos = [
        ("Tier=S+⚡⚡", [df["tier"] == "S+⚡⚡"]),
        ("Tier=S+⚡⚡+RSI<45", [df["tier"] == "S+⚡⚡", df["RSI"] < 45]),
        ("Tier=S+⚡⚡+RSI<50", [df["tier"] == "S+⚡⚡", df["RSI"] < 50]),
        ("GoldDn30d≥5", [df["goldDn_30d"] >= 5]),
        ("GoldDn30d≥5+RSI<45", [df["goldDn_30d"] >= 5, df["RSI"] < 45]),
        ("W2S", [df["is_WeakToStrong"]]),
        ("GoldGate1", [df["GoldGateOnAlgo1"] == "Y"]),
        ("Blue14d≥3", [df["blueup_14d"] >= 3]),
    ]
    
    print(f"\n   {'組合':<35} {'5日':>15} {'7日':>15} {'10日':>15}")
    print(f"   {'-'*65}")
    
    for name, conds in us_long_combos:
        mask = base_us_l.copy()
        for c in conds:
            mask = mask & c
        row = f"   {name:<35}"
        for hold in [5, 7, 10]:
            bt = vbt(df, mask, "LONG", hold, min_n=3)
            if bt:
                flag = "🔥" if bt["win_rate"] >= TARGET_WR else ""
                row += f" {bt['n']:>3}WR={bt['win_rate']:.0%}{flag}"
            else:
                row += f"    N/A    "
        print(row)
    
    print(f"\n   🌎 US SHO")
    base_us_s = (df["Country"] == "US") & df["is_GoldenPinUp"]
    us_sho_combos = [
        ("Blue7d=0", [df["blueup_7d"] == 0]),
        ("Blue14d=0", [df["blueup_14d"] == 0]),
        ("Blue7d=0+RSI>60", [df["blueup_7d"] == 0, df["RSI"] > 60]),
        ("Blue14d=0+RSI>60", [df["blueup_14d"] == 0, df["RSI"] > 60]),
        ("Blue14d=0+RSI>65", [df["blueup_14d"] == 0, df["RSI"] > 65]),
        ("Blue7d=0+RSI>55", [df["blueup_7d"] == 0, df["RSI"] > 55]),
    ]
    
    print(f"\n   {'組合':<35} {'5日':>15} {'7日':>15} {'10日':>15}")
    print(f"   {'-'*65}")
    
    for name, conds in us_sho_combos:
        mask = base_us_s.copy()
        for c in conds:
            mask = mask & c
        row = f"   {name:<35}"
        for hold in [5, 7, 10]:
            bt = vbt(df, mask, "SHO", hold, min_n=3)
            if bt:
                flag = "🔥" if bt["win_rate"] >= TARGET_WR else ""
                row += f" {bt['n']:>3}WR={bt['win_rate']:.0%}{flag}"
            else:
                row += f"    N/A    "
        print(row)
    
    # ═══ 最佳結果彙總 ═══
    print(f"\n{'='*80}")
    print(f"🏆 V3.2 最佳組合彙總 (目標≥{TARGET_WR:.0%}, n≥{MIN_N})")
    print(f"{'='*80}")
    
    # LONG
    print(f"\n   🟡 HK LONG Top 5:")
    long_sorted = sorted(best_long, key=lambda x: x[1]["win_rate"], reverse=True)
    for i, (name, bt, _) in enumerate(long_sorted[:5]):
        flag = "✅" if bt["win_rate"] >= TARGET_WR else "⚠️"
        print(f"   {i+1}. {flag} {name:<45} n={bt['n']:>4} WR={bt['win_rate']:.1%} PnL={bt['avg_pnl']:+.2f}%")
    
    # SHO
    print(f"\n   🔴 HK SHO Top 5:")
    sho_sorted = sorted(best_sho, key=lambda x: x[1]["win_rate"], reverse=True)
    for i, (name, bt, _) in enumerate(sho_sorted[:5]):
        flag = "✅" if bt["win_rate"] >= TARGET_WR else "⚠️"
        print(f"   {i+1}. {flag} {name:<45} n={bt['n']:>4} WR={bt['win_rate']:.1%} PnL={bt['avg_pnl']:+.2f}%")
    
    # ═══ 最終 14 Indicator 分配建議 ═══
    print(f"\n{'='*80}")
    print(f"📋 V3.2 最終 14 Indicator 分配建議")
    print(f"{'='*80}")
    
    print(f"""
   港股 LONG (5個):
   ┌──────┬──────────────────────────────────────────────────────┐
   │ L17  │ Cap + Tier=S+⚡⚡ + RSI<45 + Blue14d≥2              │
   │ L16  │ Cap + Tier≥S+⚡ + RSI<45 + W2S7d≥1                  │
   │ L06  │ GoldDn + W2S (無Cap)                                │
   │ L04  │ GoldDn + GoldGate1 (無Cap)                          │
   │ L03  │ Cap + RSI<45 + W2S7d≥1                             │
   └──────┴──────────────────────────────────────────────────────┘
   
   港股 SHO (3個):
   ┌──────┬──────────────────────────────────────────────────────┐
   │ S02  │ Blue30d≤1 + RSI>60 + Drop>15%                       │
   │ S01  │ Blue7d=0 + RSI>65                                   │
   │ S11  │ Blue14d=0 + RSI>60 + Drop>10%                        │
   └──────┴──────────────────────────────────────────────────────┘
   
   美股 LONG (3個):
   ┌──────┬──────────────────────────────────────────────────────┐
   │ US01 │ GoldDn + Tier=S+⚡⚡ (無Cap)                        │
   │ US02 │ GoldDn + W2S (無Cap)                                 │
   │ US03 │ GoldDn + GoldGate1 (無Cap)                           │
   └──────┴──────────────────────────────────────────────────────┘
   
   美股 SHO (3個):
   ┌──────┬──────────────────────────────────────────────────────┐
   │ US04 │ Blue14d=0 + RSI>60                                  │
   │ US05 │ Blue14d=0                                          │
   │ US06 │ Blue7d=0 + RSI>60                                  │
   └──────┴──────────────────────────────────────────────────────┘
    """)

if __name__ == "__main__":
    print("🦞 V3.2 最終優化")
    print(f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    print(f"\n📥 載入數據...")
    df = load_data()
    print(f"   總行數：{len(df):,}")
    
    exhaustive_search(df)
    
    print(f"\n💾 完成")