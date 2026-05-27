#!/usr/bin/env python3
"""
V3.2 逆向工程 — 目標勝率 70%
優化版：用向量化回測 + 貪婪搜尋
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path("/Users/ttse/.openclaw/workspace-stock-goldenpin/data/Golden Pin Stockbot - OpenClaw")
TARGET_WR = 0.70

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
    
    # 向量化回測：預計算 5 日後收盤價
    df["close_5d_future"] = df.groupby("Stock_No")["Close"].shift(-5)
    df["pnl_5d_long"] = (df["close_5d_future"] - df["Close"]) / df["Close"] * 100
    df["pnl_5d_sho"] = -df["pnl_5d_long"]
    
    return df

def vector_backtest(df, mask, direction, min_n=5):
    """向量化回測，極快"""
    d = df[mask & df["pnl_5d_long"].notna()].copy()
    if len(d) < min_n:
        return None
    pnl = d["pnl_5d_long"] if direction == "LONG" else d["pnl_5d_sho"]
    return {
        "n": len(d), "win_rate": (pnl > 0).mean(), "avg_pnl": pnl.mean(),
        "median_pnl": pnl.median(),
    }

def greedy_search(df, base_mask, direction, country, label):
    """貪婪搜尋：逐個加入最優條件"""
    print(f"\n{'='*70}")
    print(f"🔬 {label} 貪婪搜尋 — 目標勝率≥{TARGET_WR:.0%}")
    print(f"{'='*70}")
    
    # 候選條件
    if direction == "LONG":
        candidates = {
            "Tier=S+⚡⚡": df["tier"] == "S+⚡⚡",
            "Tier≥S+⚡": df["tier"].isin(["S+⚡", "S+⚡⚡"]),
            "Tier≥S+": df["tier"].isin(["S+", "S+⚡", "S+⚡⚡"]),
            "Blue7d≥1": df["blueup_7d"] >= 1,
            "Blue7d≥2": df["blueup_7d"] >= 2,
            "Blue7d≥3": df["blueup_7d"] >= 3,
            "Blue14d≥2": df["blueup_14d"] >= 2,
            "Blue14d≥3": df["blueup_14d"] >= 3,
            "Blue30d≥3": df["blueup_30d"] >= 3,
            "Blue30d≥5": df["blueup_30d"] >= 5,
            "W2S": df["is_WeakToStrong"],
            "W2S7d≥1": df["w2s_7d"] >= 1,
            "W2S14d≥1": df["w2s_14d"] >= 1,
            "RSI<25": df["RSI"] < 25,
            "RSI<30": df["RSI"] < 30,
            "RSI<35": df["RSI"] < 35,
            "RSI<40": df["RSI"] < 40,
            "RSI<45": df["RSI"] < 45,
            "RSI<50": df["RSI"] < 50,
            "GoldDn30d≥3": df["goldDn_30d"] >= 3,
            "GoldDn30d≥4": df["goldDn_30d"] >= 4,
            "GoldDn30d≥5": df["goldDn_30d"] >= 5,
            "GoldDn_filt30d≥3": df["goldDn_filt_30d_count"] >= 3,
            "GoldDn_filt30d≥4": df["goldDn_filt_30d_count"] >= 4,
            "GoldDn_filt30d≥5": df["goldDn_filt_30d_count"] >= 5,
            "GoldGate1": df["GoldGateOnAlgo1"] == "Y",
            "NoRecentGd": df["no_recent_gd"],
            "CapFilter": df["goldDn_filtered"],
            "Drop<15%": df["drop_30d_pct"] < 0.15,
            "Drop<10%": df["drop_30d_pct"] < 0.10,
        }
    else:  # SHO
        candidates = {
            "S2W": df["is_StrongToWeak"],
            "Blue7d=0": df["blueup_7d"] == 0,
            "Blue7d≤1": df["blueup_7d"] <= 1,
            "Blue14d=0": df["blueup_14d"] == 0,
            "Blue14d≤1": df["blueup_14d"] <= 1,
            "Blue30d≤1": df["blueup_30d"] <= 1,
            "Drop>10%": df["drop_10pct"],
            "Drop>15%": df["drop_15pct"],
            "RSI>55": df["RSI"] > 55,
            "RSI>60": df["RSI"] > 60,
            "RSI>65": df["RSI"] > 65,
            "RSI>70": df["RSI"] > 70,
            "RSI>75": df["RSI"] > 75,
            "GoldDn30d=0": df["goldDn_30d"] == 0,
            "GoldDn30d≤1": df["goldDn_30d"] <= 1,
            "GoldDn14d=0": df["goldDn_14d"] == 0,
            "GoldGate1": df["GoldGateOnAlgo1"] == "Y",
        }
    
    exclusive = {
        "Tier=S+⚡⚡": "tier", "Tier≥S+⚡": "tier", "Tier≥S+": "tier",
        "Blue7d≥1": "blue", "Blue7d≥2": "blue", "Blue7d≥3": "blue",
        "Blue14d≥2": "blue", "Blue14d≥3": "blue", "Blue30d≥3": "blue", "Blue30d≥5": "blue",
        "Blue7d=0": "blue_s", "Blue7d≤1": "blue_s", "Blue14d=0": "blue_s", "Blue14d≤1": "blue_s", "Blue30d≤1": "blue_s",
        "RSI<25": "rsi_l", "RSI<30": "rsi_l", "RSI<35": "rsi_l", "RSI<40": "rsi_l", "RSI<45": "rsi_l", "RSI<50": "rsi_l",
        "RSI>55": "rsi_h", "RSI>60": "rsi_h", "RSI>65": "rsi_h", "RSI>70": "rsi_h", "RSI>75": "rsi_h",
        "GoldDn30d≥3": "gdn30", "GoldDn30d≥4": "gdn30", "GoldDn30d≥5": "gdn30",
        "GoldDn_filt30d≥3": "gdnf30", "GoldDn_filt30d≥4": "gdnf30", "GoldDn_filt30d≥5": "gdnf30",
        "GoldDn30d=0": "gdn0", "GoldDn30d≤1": "gdn0", "GoldDn14d=0": "gdn0",
        "Drop>10%": "drop", "Drop>15%": "drop", "Drop<15%": "drop", "Drop<10%": "drop",
        "W2S": "w2s", "W2S7d≥1": "w2s", "W2S14d≥1": "w2s",
    }
    
    # Step 1: 單條件
    print(f"\n   Step 1: 單條件")
    print(f"   {'條件':<25} {'信號':>5} {'勝率':>7} {'PnL':>9}")
    print(f"   {'-'*50}")
    
    single_scores = {}
    for name, cond in candidates.items():
        mask = base_mask & cond
        bt = vector_backtest(df, mask, direction, min_n=5)
        if bt:
            single_scores[name] = (bt, cond)
            flag = "🔥" if bt["win_rate"] >= TARGET_WR else ""
            print(f"   {name:<25} {bt['n']:>5} {bt['win_rate']:>6.1%}{flag} {bt['avg_pnl']:>+8.2f}%")
    
    # Step 2: 貪婪法 — 逐個加入最高勝率條件
    print(f"\n   Step 2: 貪婪搜尋 (逐個加最優條件)")
    print(f"   {'步驟':>4} {'加入':<25} {'信號':>5} {'勝率':>7} {'PnL':>9} {'累計條件'}")
    print(f"   {'-'*90}")
    
    current_mask = base_mask.copy()
    used_conditions = []
    used_groups = set()
    best_results = []
    
    for step in range(6):  # 最多加 6 個條件
        best_wr = 0
        best_name = None
        best_bt = None
        best_cond = None
        
        for name, (bt, cond) in single_scores.items():
            if name in used_conditions:
                continue
            grp = exclusive.get(name)
            if grp and grp in used_groups:
                continue
            
            test_mask = current_mask & cond
            test_bt = vector_backtest(df, test_mask, direction, min_n=3)
            if test_bt and test_bt["win_rate"] > best_wr:
                best_wr = test_bt["win_rate"]
                best_name = name
                best_bt = test_bt
                best_cond = cond
        
        if best_name is None:
            break
        
        current_mask = current_mask & best_cond
        used_conditions.append(best_name)
        grp = exclusive.get(best_name)
        if grp:
            used_groups.add(grp)
        
        best_results.append({
            "step": step + 1,
            "name": best_name,
            "n": best_bt["n"],
            "win_rate": best_bt["win_rate"],
            "avg_pnl": best_bt["avg_pnl"],
            "conditions": " + ".join(used_conditions),
        })
        
        flag = " 🎯達標!" if best_bt["win_rate"] >= TARGET_WR else ""
        print(f"   {step+1:>4} {best_name:<25} {best_bt['n']:>5} {best_bt['win_rate']:>6.1%} {best_bt['avg_pnl']:>+8.2f}%  {' + '.join(used_conditions)}{flag}")
        
        if best_bt["win_rate"] >= TARGET_WR and best_bt["n"] >= 5:
            print(f"\n   ✅ 達標！最終組合：{' + '.join(used_conditions)}")
            break
        if best_bt["n"] < 3:
            print(f"\n   ⚠️ 樣本太少，停止搜尋")
            break
    
    # Step 3: 如果未達標，列出所有組合嘅勝率
    if not any(r["win_rate"] >= TARGET_WR and r["n"] >= 5 for r in best_results):
        print(f"\n   ⚠️ 貪婪法未達 {TARGET_WR:.0%}")
        print(f"\n   嘗試極致篩選：")
        
        # 嘗試最嚴格組合
        strict_tests = []
        if direction == "LONG":
            # 測試各種嚴格組合
            for tier_c in ["Tier=S+⚡⚡", "Tier≥S+⚡"]:
                for blue_c in ["Blue30d≥5", "Blue30d≥3", "Blue14d≥3", "Blue14d≥2"]:
                    for rsi_c in ["RSI<30", "RSI<35", "RSI<40", "RSI<45"]:
                        for extra in ["GoldDn_filt30d≥4", "GoldDn_filt30d≥5", "GoldGate1", "NoRecentGd"]:
                            if tier_c not in candidates or blue_c not in candidates or rsi_c not in candidates or extra not in candidates:
                                continue
                            mask = base_mask & candidates[tier_c] & candidates[blue_c] & candidates[rsi_c] & candidates[extra]
                            bt = vector_backtest(df, mask, direction, min_n=3)
                            if bt and bt["win_rate"] >= 0.55:
                                strict_tests.append((f"{tier_c}+{blue_c}+{rsi_c}+{extra}", bt))
        else:  # SHO
            for blue_c in ["Blue7d=0", "Blue14d=0", "Blue14d≤1"]:
                for rsi_c in ["RSI>70", "RSI>75", "RSI>65"]:
                    for extra in ["Drop>15%", "Drop>20%", "GoldDn30d=0", "GoldDn14d=0"]:
                        if blue_c not in candidates or rsi_c not in candidates or extra not in candidates:
                            continue
                        mask = base_mask & candidates[blue_c] & candidates[rsi_c] & candidates[extra]
                        bt = vector_backtest(df, mask, direction, min_n=3)
                        if bt and bt["win_rate"] >= 0.55:
                            strict_tests.append((f"{blue_c}+{rsi_c}+{extra}", bt))
        
        strict_tests.sort(key=lambda x: x[1]["win_rate"], reverse=True)
        print(f"   {'組合':<60} {'信號':>5} {'勝率':>7} {'PnL':>9}")
        print(f"   {'-'*85}")
        for name, bt in strict_tests[:20]:
            flag = "🔥" if bt["win_rate"] >= TARGET_WR else ""
            print(f"   {name:<60} {bt['n']:>5} {bt['win_rate']:>6.1%}{flag} {bt['avg_pnl']:>+8.2f}%")
    
    return best_results

if __name__ == "__main__":
    print("🦞 V3.2 逆向工程 — 目標勝率 70%")
    print(f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    print(f"\n📥 載入數據...")
    df = load_data()
    print(f"   總行數：{len(df):,} | 股票數：{df['Stock_No'].nunique()}")
    print(f"   GoldDn：{int(df['is_GoldenPinDown'].sum()):,} | Filtered：{int(df['goldDn_filtered'].sum()):,}")
    print(f"   GoldUp：{int(df['is_GoldenPinUp'].sum()):,}")
    
    # HK LONG
    base_hk_long = (df["Country"] == "HK") & df["is_GoldenPinDown"]
    hk_long = greedy_search(df, base_hk_long, "LONG", "HK", "港股 LONG")
    
    # HK SHO
    base_hk_sho = (df["Country"] == "HK") & df["is_GoldenPinUp"]
    hk_sho = greedy_search(df, base_hk_sho, "SHO", "HK", "港股 SHO")
    
    # US LONG
    base_us_long = (df["Country"] == "US") & df["is_GoldenPinDown"]
    us_long = greedy_search(df, base_us_long, "LONG", "US", "美股 LONG")
    
    # US SHO
    base_us_sho = (df["Country"] == "US") & df["is_GoldenPinUp"]
    us_sho = greedy_search(df, base_us_sho, "SHO", "US", "美股 SHO")
    
    print(f"\n{'='*70}")
    print(f"📝 V3.2 最終建議")
    print(f"{'='*70}")
    for label, results in [("HK LONG", hk_long), ("HK SHO", hk_sho), ("US LONG", us_long), ("US SHO", us_sho)]:
        if results:
            last = results[-1]
            print(f"   {label}: {last['conditions']} → WR={last['win_rate']:.1%} n={last['n']} PnL={last['avg_pnl']:+.2f}%")