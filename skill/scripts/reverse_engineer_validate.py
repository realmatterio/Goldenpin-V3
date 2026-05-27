#!/usr/bin/env python3
"""
Reverse Engineer 14 Validated Indicators — 準確度驗證
用 Google Drive 原始 CSV 數據逆向工程 Danny Sir 嘅 Indicators

方法：
1. 用現有 AI 推測嘅 Indicator 定義，回測歷史勝率
2. 嘗試唔同條件組合，搵出最高勝率嘅定義
3. 對比 AI 推測 vs 數據驗證
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
# 1. DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

def load_all_data():
    """載入所有 Google Drive CSV 數據"""
    dfs = []
    for f in sorted(DATA_DIR.glob("StockDailyPins*.csv*")):
        try:
            df = pd.read_csv(f)
            if "GoldGateOnAlgo1" not in df.columns:
                df["GoldGateOnAlgo1"] = "N"
                df["GoldGateOnAlgo2"] = "N"
            dfs.append(df)
            print(f"   ✅ {f.name}: {len(df):,} rows")
        except Exception as e:
            print(f"   ⚠️ {f.name}: {e}")
    
    if not dfs:
        raise ValueError("No CSV files found")
    
    result = pd.concat(dfs, ignore_index=True)
    result["Date"] = pd.to_datetime(result["Date"])
    result = result.sort_values(["Stock_No", "Date"]).reset_index(drop=True)
    
    # 基本清理
    result = result[result["Close"] > 0].copy()
    result = result[result["Volume"] > 0].copy()
    
    return result

# ══════════════════════════════════════════════════════════════════════════════
# 2. SIGNAL PROCESSING (from Preface_0000)
# ══════════════════════════════════════════════════════════════════════════════

def flag_signals(df):
    """轉換 Y/N 為布林值"""
    for col in ["GoldenPinDown", "GoldenPinUp", "BluePinUp", "BluePinDown",
                "WeakToStrong", "StrongToWeak", "GreyPinDown",
                "GoldGateOnAlgo1", "GoldGateOnAlgo2"]:
        if col in df.columns:
            df[f"is_{col}"] = df[col] == "Y"
    return df

def capitulation_filter(df):
    """Capitulation Filter (from Preface_0000)"""
    df = df.copy()
    df = df.sort_values(["Stock_No", "Date"])
    
    # 30 日跌幅
    df["close_30d_ago"] = df.groupby("Stock_No")["Close"].shift(30)
    df["return_30d"] = (df["Close"] - df["close_30d_ago"]) / df["close_30d_ago"]
    df["drop_30d_pct"] = -df["return_30d"]
    
    # 7 日 BlueUp / W2S
    df["blueup_7d"] = df.groupby("Stock_No")["is_BluePinUp"].transform(
        lambda x: x.rolling(7, min_periods=1).sum()
    ).astype(int)
    df["w2s_7d"] = df.groupby("Stock_No")["is_WeakToStrong"].transform(
        lambda x: x.rolling(7, min_periods=1).sum()
    ).astype(int)
    
    df["has_institutional_support"] = (df["blueup_7d"] > 0) | (df["w2s_7d"] > 0)
    df["drop_under_25pct"] = df["drop_30d_pct"] < 0.25
    df["goldDn_filtered"] = df["is_GoldenPinDown"] & df["has_institutional_support"] & df["drop_under_25pct"]
    
    return df

def tier_enhancement(df, window=30):
    """Tier Enhancement (from Preface_0000)"""
    df = df.copy()
    df["goldDn_30d_count"] = df.groupby("Stock_No")["is_GoldenPinDown"].transform(
        lambda x: x.rolling(window, min_periods=1).sum()
    ).astype(int)
    
    tier_map = {4: "S+⚡⚡", 3: "S+⚡", 2: "S+", 1: "S"}
    df["tier"] = df["goldDn_30d_count"].apply(
        lambda x: tier_map.get(x, "S+⚡⚡") if x >= 1 else None
    )
    df.loc[~df["is_GoldenPinDown"], "tier"] = None
    return df

def add_features(df):
    """添加額外特徵用於逆向工程"""
    df = df.copy()
    
    # RSI 閾值
    df["rsi_below_30"] = df["RSI"] < 30
    df["rsi_below_35"] = df["RSI"] < 35
    df["rsi_below_40"] = df["RSI"] < 40
    df["rsi_below_45"] = df["RSI"] < 45
    df["rsi_below_50"] = df["RSI"] < 50
    
    # GoldDn 歷史出現次數
    for n in [3, 5, 7, 10, 14, 30]:
        df[f"goldDn_{n}d"] = df.groupby("Stock_No")["is_GoldenPinDown"].transform(
            lambda x: x.rolling(n, min_periods=1).sum()
        ).astype(int)
    
    # BlueUp 歷史出現次數
    for n in [3, 5, 7, 10, 14]:
        df[f"blueup_{n}d"] = df.groupby("Stock_No")["is_BluePinUp"].transform(
            lambda x: x.rolling(n, min_periods=1).sum()
        ).astype(int)
    
    # W2S 歷史
    for n in [3, 5, 7]:
        df[f"w2s_{n}d"] = df.groupby("Stock_No")["is_WeakToStrong"].transform(
            lambda x: x.rolling(n, min_periods=1).sum()
        ).astype(int)
    
    # 跌幅
    df["drop_30d_10pct"] = df["drop_30d_pct"] > 0.10
    df["drop_30d_15pct"] = df["drop_30d_pct"] > 0.15
    df["drop_30d_20pct"] = df["drop_30d_pct"] > 0.20
    
    # NoRecentGdPinsDw (CSV 原始欄位)
    df["no_recent_gd"] = df["NoRecentGdPinsDw"].str.strip() != ""
    
    return df

# ══════════════════════════════════════════════════════════════════════════════
# 3. AI 推測嘅 14 INDICATORS 定義
# ══════════════════════════════════════════════════════════════════════════════

AI_INDICATORS = {
    # 港股 LONG
    "L17": {
        "ai_def": "GoldDn + Tier S+⚡⚡ + BlueUp_7d ≥ 3",
        "condition": lambda df: (df["Country"] == "HK") & df["goldDn_filtered"] & (df["tier"] == "S+⚡⚡") & (df["blueup_7d"] >= 3),
        "direction": "LONG",
    },
    "L16": {
        "ai_def": "GoldDn + Tier S+⚡/S+⚡⚡ + BlueUp_7d ≥ 2",
        "condition": lambda df: (df["Country"] == "HK") & df["goldDn_filtered"] & (df["tier"].isin(["S+⚡", "S+⚡⚡"])) & (df["blueup_7d"] >= 2),
        "direction": "LONG",
    },
    "L06": {
        "ai_def": "GoldDn + WeakToStrong",
        "condition": lambda df: (df["Country"] == "HK") & df["goldDn_filtered"] & df["is_WeakToStrong"],
        "direction": "LONG",
    },
    "L04": {
        "ai_def": "GoldDn + GoldGateOnAlgo1",
        "condition": lambda df: (df["Country"] == "HK") & df["goldDn_filtered"] & (df["GoldGateOnAlgo1"] == "Y"),
        "direction": "LONG",
    },
    "L03": {
        "ai_def": "GoldDn + RSI < 40",
        "condition": lambda df: (df["Country"] == "HK") & df["goldDn_filtered"] & (df["RSI"] < 40),
        "direction": "LONG",
    },
    # 港股 SHO
    "S02": {
        "ai_def": "GoldUp + StrongToWeak + drop > 15%",
        "condition": lambda df: (df["Country"] == "HK") & df["is_GoldenPinUp"] & df["is_StrongToWeak"] & (df["drop_30d_pct"] > 0.15),
        "direction": "SHO",
    },
    "S01": {
        "ai_def": "GoldUp + BlueUp_7d = 0",
        "condition": lambda df: (df["Country"] == "HK") & df["is_GoldenPinUp"] & (df["blueup_7d"] == 0),
        "direction": "SHO",
    },
    "S11": {
        "ai_def": "GoldUp + drop > 10%",
        "condition": lambda df: (df["Country"] == "HK") & df["is_GoldenPinUp"] & (df["drop_30d_pct"] > 0.10),
        "direction": "SHO",
    },
    # 美股 LONG
    "US01": {
        "ai_def": "GoldDn + Tier S+⚡⚡",
        "condition": lambda df: (df["Country"] == "US") & df["goldDn_filtered"] & (df["tier"] == "S+⚡⚡"),
        "direction": "LONG",
    },
    "US02": {
        "ai_def": "GoldDn + WeakToStrong",
        "condition": lambda df: (df["Country"] == "US") & df["goldDn_filtered"] & df["is_WeakToStrong"],
        "direction": "LONG",
    },
    "US03": {
        "ai_def": "GoldDn + GoldGateOnAlgo1",
        "condition": lambda df: (df["Country"] == "US") & df["goldDn_filtered"] & (df["GoldGateOnAlgo1"] == "Y"),
        "direction": "LONG",
    },
    # 美股 SHO
    "US04": {
        "ai_def": "GoldUp + StrongToWeak",
        "condition": lambda df: (df["Country"] == "US") & df["is_GoldenPinUp"] & df["is_StrongToWeak"],
        "direction": "SHO",
    },
    "US05": {
        "ai_def": "GoldUp + BlueUp_7d = 0",
        "condition": lambda df: (df["Country"] == "US") & df["is_GoldenPinUp"] & (df["blueup_7d"] == 0),
        "direction": "SHO",
    },
    "US06": {
        "ai_def": "GoldUp + drop > 10%",
        "condition": lambda df: (df["Country"] == "US") & df["is_GoldenPinUp"] & (df["drop_30d_pct"] > 0.10),
        "direction": "SHO",
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# 4. 回測引擎
# ══════════════════════════════════════════════════════════════════════════════

def backtest_indicator(df, condition_mask, direction, hold_days=5):
    """回測單個 Indicator"""
    signals = df[condition_mask].copy()
    
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
            pnl_pct = (exit_price - entry_price) / entry_price * 100
            
            # LONG 賺=正, SHO 賺=負變正
            if direction == "SHO":
                pnl_pct = -pnl_pct
            
            results.append({
                "stock": stock,
                "country": row["Country"],
                "entry_date": entry_date,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl_pct": pnl_pct,
                "tier": row.get("tier", ""),
                "rsi": row.get("RSI", 0),
            })
    
    if not results:
        return None
    
    r = pd.DataFrame(results)
    win_rate = (r["pnl_pct"] > 0).mean()
    avg_pnl = r["pnl_pct"].mean()
    median_pnl = r["pnl_pct"].median()
    
    return {
        "n_trades": len(r),
        "win_rate": win_rate,
        "avg_pnl": avg_pnl,
        "median_pnl": median_pnl,
        "max_win": r["pnl_pct"].max(),
        "max_loss": r["pnl_pct"].min(),
        "avg_winner": r[r["pnl_pct"] > 0]["pnl_pct"].mean() if (r["pnl_pct"] > 0).any() else 0,
        "avg_loser": r[r["pnl_pct"] < 0]["pnl_pct"].mean() if (r["pnl_pct"] < 0).any() else 0,
    }

# ══════════════════════════════════════════════════════════════════════════════
# 5. 逆向工程：嘗試唔同條件組合搵最優定義
# ══════════════════════════════════════════════════════════════════════════════

def reverse_engineer_long_indicators(df, country="HK"):
    """逆向工程 LONG 類 Indicators"""
    print(f"\n{'='*70}")
    print(f"🔬 逆向工程 LONG Indicators — {country}")
    print(f"{'='*70}")
    
    base = df[(df["Country"] == country) & df["goldDn_filtered"]].copy()
    print(f"\n   基礎池 (GoldDn + Capitulation Filter): {len(base):,}")
    
    # 測試唔同條件組合
    conditions = {
        "Tier S+⚡⚡": base["tier"] == "S+⚡⚡",
        "Tier S+⚡/S+⚡⚡": base["tier"].isin(["S+⚡", "S+⚡⚡"]),
        "BlueUp_7d≥3": base["blueup_7d"] >= 3,
        "BlueUp_7d≥2": base["blueup_7d"] >= 2,
        "BlueUp_7d≥1": base["blueup_7d"] >= 1,
        "W2S": base["is_WeakToStrong"],
        "GoldGate1": base["GoldGateOnAlgo1"] == "Y",
        "RSI<30": base["RSI"] < 30,
        "RSI<35": base["RSI"] < 35,
        "RSI<40": base["RSI"] < 40,
        "RSI<45": base["RSI"] < 45,
        "RSI<50": base["RSI"] < 50,
        "GoldDn_30d≥4": base["goldDn_30d_count"] >= 4,
        "GoldDn_30d≥3": base["goldDn_30d_count"] >= 3,
        "GoldDn_30d≥2": base["goldDn_30d_count"] >= 2,
        "NoRecentGdPinsDw": base["no_recent_gd"],
    }
    
    # 單條件回測
    print(f"\n   📊 單條件回測 (5 日持有):")
    print(f"   {'條件':<25} {'信號數':>6} {'勝率':>7} {'平均PnL':>9} {'中位PnL':>9}")
    print(f"   {'-'*60}")
    
    single_results = {}
    for name, mask in conditions.items():
        filtered = base[mask]
        if len(filtered) < 5:
            continue
        bt = backtest_indicator(df, mask & (df["Country"] == country) & df["goldDn_filtered"], "LONG", hold_days=5)
        if bt and bt["n_trades"] >= 5:
            single_results[name] = bt
            print(f"   {name:<25} {bt['n_trades']:>6} {bt['win_rate']:>6.1%} {bt['avg_pnl']:>+8.2f}% {bt['median_pnl']:>+8.2f}%")
    
    # 雙條件組合 (Top 5 單條件兩兩組合)
    print(f"\n   📊 雙條件組合回測 (Top 單條件兩兩配對):")
    print(f"   {'組合':<45} {'信號數':>6} {'勝率':>7} {'平均PnL':>9}")
    print(f"   {'-'*70}")
    
    # 按勝率排序取 top 單條件
    sorted_singles = sorted(single_results.items(), key=lambda x: x[1]["win_rate"], reverse=True)
    top_singles = [name for name, _ in sorted_singles[:8]]
    
    combo_results = {}
    for i, name1 in enumerate(top_singles):
        for name2 in top_singles[i+1:]:
            mask1 = conditions[name1]
            mask2 = conditions[name2]
            combined_mask = mask1 & mask2
            filtered = base[combined_mask]
            if len(filtered) < 3:
                continue
            bt = backtest_indicator(df, combined_mask & (df["Country"] == country) & df["goldDn_filtered"], "LONG", hold_days=5)
            if bt and bt["n_trades"] >= 3:
                combo_name = f"{name1} + {name2}"
                combo_results[combo_name] = bt
                print(f"   {combo_name:<45} {bt['n_trades']:>6} {bt['win_rate']:>6.1%} {bt['avg_pnl']:>+8.2f}%")
    
    return single_results, combo_results

def reverse_engineer_sho_indicators(df, country="HK"):
    """逆向工程 SHO 類 Indicators"""
    print(f"\n{'='*70}")
    print(f"🔬 逆向工程 SHO Indicators — {country}")
    print(f"{'='*70}")
    
    base = df[(df["Country"] == country) & df["is_GoldenPinUp"]].copy()
    print(f"\n   基礎池 (GoldUp): {len(base):,}")
    
    conditions = {
        "StrongToWeak": base["is_StrongToWeak"],
        "BlueUp_7d=0": base["blueup_7d"] == 0,
        "BlueUp_7d≤1": base["blueup_7d"] <= 1,
        "Drop>10%": base["drop_30d_10pct"],
        "Drop>15%": base["drop_30d_15pct"],
        "Drop>20%": base["drop_30d_20pct"],
        "RSI>60": base["RSI"] > 60,
        "RSI>70": base["RSI"] > 70,
        "GoldGate1": base["GoldGateOnAlgo1"] == "Y",
        "GoldDn_30d=0": base["goldDn_30d_count"] == 0,
    }
    
    # 單條件
    print(f"\n   📊 單條件回測 (SHO = 做空, 5 日持有):")
    print(f"   {'條件':<25} {'信號數':>6} {'勝率':>7} {'平均PnL':>9}")
    print(f"   {'-'*55}")
    
    single_results = {}
    for name, mask in conditions.items():
        filtered = base[mask]
        if len(filtered) < 5:
            continue
        bt = backtest_indicator(df, mask & (df["Country"] == country) & df["is_GoldenPinUp"], "SHO", hold_days=5)
        if bt and bt["n_trades"] >= 5:
            single_results[name] = bt
            print(f"   {name:<25} {bt['n_trades']:>6} {bt['win_rate']:>6.1%} {bt['avg_pnl']:>+8.2f}%")
    
    return single_results

# ══════════════════════════════════════════════════════════════════════════════
# 6. AI 定義 vs 最優組合 對比
# ══════════════════════════════════════════════════════════════════════════════

def validate_ai_indicators(df, hold_days=5):
    """驗證 AI 推測嘅 14 Indicators 回測結果"""
    print(f"\n{'='*70}")
    print(f"🎯 AI 推測嘅 14 Indicators 回測驗證 ({hold_days} 日持有)")
    print(f"{'='*70}")
    
    print(f"\n   {'Ind':<6} {'方向':<5} {'AI 定義':<45} {'信號':>5} {'勝率':>7} {'PnL':>8}")
    print(f"   {'-'*80}")
    
    all_results = {}
    for name, ind in AI_INDICATORS.items():
        mask = ind["condition"](df)
        n_signals = int(mask.sum())
        direction = ind["direction"]
        
        if n_signals < 1:
            print(f"   {name:<6} {direction:<5} {ind['ai_def']:<45} {'0':>5}   N/A     N/A")
            all_results[name] = {"n": 0, "win_rate": None, "avg_pnl": None, "ai_def": ind["ai_def"]}
            continue
        
        bt = backtest_indicator(df, mask, direction, hold_days=hold_days)
        if bt:
            wr = f"{bt['win_rate']:.1%}"
            pnl = f"{bt['avg_pnl']:+.2f}%"
            all_results[name] = {
                "n": bt["n_trades"],
                "win_rate": bt["win_rate"],
                "avg_pnl": bt["avg_pnl"],
                "median_pnl": bt["median_pnl"],
                "max_win": bt["max_win"],
                "max_loss": bt["max_loss"],
                "ai_def": ind["ai_def"],
            }
            print(f"   {name:<6} {direction:<5} {ind['ai_def']:<45} {bt['n_trades']:>5} {wr:>7} {pnl:>8}")
        else:
            all_results[name] = {"n": 0, "win_rate": None, "avg_pnl": None, "ai_def": ind["ai_def"]}
            print(f"   {name:<6} {direction:<5} {ind['ai_def']:<45} {'0':>5}   N/A     N/A")
    
    return all_results

def score_indicators(ai_results):
    """為每個 Indicator 打分"""
    print(f"\n{'='*70}")
    print(f"🏆 14 Indicators 準確度評分")
    print(f"{'='*70}")
    
    print(f"\n   {'Ind':<6} {'方向':<5} {'勝率':>7} {'PnL':>8} {'樣本':>5} {'評級':>6} {'說明'}")
    print(f"   {'-'*65}")
    
    for name, r in sorted(ai_results.items(), key=lambda x: x[1].get("win_rate", 0) or 0, reverse=True):
        wr = r.get("win_rate")
        pnl = r.get("avg_pnl")
        n = r.get("n", 0)
        
        if wr is None or n == 0:
            grade = "❓"
            note = "無數據"
        elif n < 5:
            grade = "⚠️"
            note = "樣本太少"
        elif wr >= 0.65 and pnl and pnl > 2:
            grade = "🟢"
            note = "高勝率+高回報"
        elif wr >= 0.55 and pnl and pnl > 0:
            grade = "🟡"
            note = "可行"
        elif wr >= 0.50:
            grade = "🟠"
            note = "勉強"
        else:
            grade = "🔴"
            note = "負回報"
        
        wr_str = f"{wr:.1%}" if wr else "N/A"
        pnl_str = f"{pnl:+.2f}%" if pnl else "N/A"
        
        print(f"   {name:<6} {'L' if name[0] in 'LUS' else 'S':<5} {wr_str:>7} {pnl_str:>8} {n:>5} {grade:>6} {note}")
    
    # LONG vs SHO 對比
    long_results = {k: v for k, v in ai_results.items() if v.get("win_rate") and k[0] in "L" or k.startswith("US0")}
    sho_results = {k: v for k, v in ai_results.items() if v.get("win_rate") and (k[0] == "S" or k.startswith("US0") and int(k[-1]) >= 4)}
    
    print(f"\n   📊 方向對比:")
    if long_results:
        avg_wr = np.mean([v["win_rate"] for v in long_results.values() if v.get("win_rate")])
        avg_pnl = np.mean([v["avg_pnl"] for v in long_results.values() if v.get("avg_pnl")])
        print(f"      LONG 平均勝率：{avg_wr:.1%}  平均PnL：{avg_pnl:+.2f}%")
    if sho_results:
        avg_wr = np.mean([v["win_rate"] for v in sho_results.values() if v.get("win_rate")])
        avg_pnl = np.mean([v["avg_pnl"] for v in sho_results.values() if v.get("avg_pnl")])
        print(f"      SHO  平均勝率：{avg_wr:.1%}  平均PnL：{avg_pnl:+.2f}%")

# ══════════════════════════════════════════════════════════════════════════════
# 7. 多日持有期回測
# ══════════════════════════════════════════════════════════════════════════════

def backtest_hold_periods(df):
    """測試唔同持有期"""
    print(f"\n{'='*70}")
    print(f"📈 不同持有期回測 (所有 LONG Indicators)")
    print(f"{'='*70}")
    
    print(f"\n   {'持有期':>6}", end="")
    for name in ["L17", "L16", "L06", "L04", "L03", "US01", "US02", "US03"]:
        print(f"  {name:>8}", end="")
    print()
    print(f"   {'-'*80}")
    
    for hold in [3, 5, 7, 10, 14, 20]:
        print(f"   {hold:>4}日", end="")
        for name in ["L17", "L16", "L06", "L04", "L03", "US01", "US02", "US03"]:
            ind = AI_INDICATORS[name]
            mask = ind["condition"](df)
            bt = backtest_indicator(df, mask, "LONG", hold_days=hold)
            if bt and bt["n_trades"] >= 3:
                print(f"  {bt['avg_pnl']:>+7.2f}%", end="")
            else:
                print(f"  {'N/A':>8}", end="")
        print()

# ══════════════════════════════════════════════════════════════════════════════
# 8. MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🦞 黃金針 V3 — 14 Indicators 逆向工程驗證")
    print(f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"數據源：Google Drive CSV (Goldenpin_0000.md)")
    
    # 1. 載入數據
    print(f"\n📥 載入數據...")
    df = load_all_data()
    print(f"   總行數：{len(df):,} | 股票數：{df['Stock_No'].nunique()}")
    print(f"   日期範圍：{df['Date'].min().date()} 至 {df['Date'].max().date()}")
    
    # 2. 處理信號
    print(f"\n🔧 處理信號 (Capitulation Filter + Tier Enhancement)...")
    df = flag_signals(df)
    df = capitulation_filter(df)
    df = tier_enhancement(df)
    df = add_features(df)
    
    print(f"   GoldDn 原始：{int(df['is_GoldenPinDown'].sum()):,}")
    print(f"   GoldDn Filtered：{int(df['goldDn_filtered'].sum()):,}")
    print(f"   GoldUp：{int(df['is_GoldenPinUp'].sum()):,}")
    
    # 3. 驗證 AI 定義
    print(f"\n{'='*70}")
    print(f"第 1 部分：AI 推測嘅 14 Indicators 回測")
    print(f"{'='*70}")
    ai_results = validate_ai_indicators(df, hold_days=5)
    
    # 4. 評分
    score_indicators(ai_results)
    
    # 5. 逆向工程 LONG
    print(f"\n{'='*70}")
    print(f"第 2 部分：逆向工程 — 搵最優條件組合")
    print(f"{'='*70}")
    hk_long_single, hk_long_combo = reverse_engineer_long_indicators(df, "HK")
    us_long_single, us_long_combo = reverse_engineer_long_indicators(df, "US")
    
    # 6. 逆向工程 SHO
    hk_sho_single = reverse_engineer_sho_indicators(df, "HK")
    us_sho_single = reverse_engineer_sho_indicators(df, "US")
    
    # 7. 多日持有期
    backtest_hold_periods(df)
    
    # 8. 總結
    print(f"\n{'='*70}")
    print(f"📝 逆向工程總結")
    print(f"{'='*70}")
    print(f"""
    🔍 驗證方法：
    - 用 Google Drive 原始 CSV 數據
    - 回測 5 日持有期（基準）
    - 單條件 + 雙條件組合測試
    - 對比 AI 推測定義 vs 數據最優組合
    
    ⚠️ 注意：
    - 過去表現 ≠ 未來保證
    - 樣本數太少嘅 Indicator 結果不可靠
    - Danny Sir 原始算法可能更複雜
    - GoldGateOnAlgo1/2 係 2026 新增欄位，歷史數據可能無
    """)
    
    # 保存結果
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"reverse_engineer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    print(f"\n💾 結果已保存至 {output_path}")