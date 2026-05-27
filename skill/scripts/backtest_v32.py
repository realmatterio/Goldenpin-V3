#!/usr/bin/env python3
"""V3.2 正式回測"""
import pandas as pd, numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path("../data/pretrain")

def load():
    dfs = []
    for f in sorted(DATA_DIR.glob("StockDailyPins*.csv*")):
        try:
            df = pd.read_csv(f)
            if "GoldGateOnAlgo1" not in df.columns:
                df["GoldGateOnAlgo1"] = "N"; df["GoldGateOnAlgo2"] = "N"
            dfs.append(df)
        except: pass
    df = pd.concat(dfs, ignore_index=True)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values(["Stock_No","Date"]).reset_index(drop=True)
    df = df[(df["Close"]>0)&(df["Volume"]>0)].copy()
    for c in ["GoldenPinDown","GoldenPinUp","BluePinUp","BluePinDown","WeakToStrong","StrongToWeak","GreyPinDown","GoldGateOnAlgo1","GoldGateOnAlgo2"]:
        if c in df.columns: df[f"is_{c}"] = df[c]=="Y"
    df["close_30d_ago"] = df.groupby("Stock_No")["Close"].shift(30)
    df["drop_30d_pct"] = -(df["Close"]-df["close_30d_ago"])/df["close_30d_ago"]
    for n in [7,14,30]:
        df[f"blueup_{n}d"] = df.groupby("Stock_No")["is_BluePinUp"].transform(lambda x: x.rolling(n,min_periods=1).sum()).astype(int)
    df["w2s_7d"] = df.groupby("Stock_No")["is_WeakToStrong"].transform(lambda x: x.rolling(7,min_periods=1).sum()).astype(int)
    df["has_inst"] = (df["blueup_7d"]>0)|(df["w2s_7d"]>0)
    df["goldDn_filtered"] = df["is_GoldenPinDown"] & df["has_inst"] & (df["drop_30d_pct"]<0.25)
    df["goldDn_30d"] = df.groupby("Stock_No")["is_GoldenPinDown"].transform(lambda x: x.rolling(30,min_periods=1).sum()).astype(int)
    tm = {4:"S+⚡⚡",3:"S+⚡",2:"S+",1:"S"}
    df["tier"] = df["goldDn_30d"].apply(lambda x: tm.get(x,"S+⚡⚡") if x>=1 else None)
    df.loc[~df["is_GoldenPinDown"],"tier"] = None
    for h in [5,7,14]:
        df[f"fut_{h}d"] = df.groupby("Stock_No")["Close"].shift(-h)
        df[f"pnl_{h}d"] = (df[f"fut_{h}d"]-df["Close"])/df["Close"]*100
    return df

def vbt(df, mask, d, h=5, mn=3):
    d2 = df[mask & df[f"pnl_{h}d"].notna()]
    if len(d2)<mn: return None
    p = d2[f"pnl_{h}d"] if d=="LONG" else -d2[f"pnl_{h}d"]
    return {"n":len(d2),"wr":(p>0).mean(),"pnl":p.mean(),"med":p.median()}

if __name__ == "__main__":
    print("🦞 Goldenpin V3.2 正式回測")
    print(f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    df = load()
    print(f"數據：{len(df):,} | GoldDn={int(df['is_GoldenPinDown'].sum()):,} | Filtered={int(df['goldDn_filtered'].sum()):,} | GoldUp={int(df['is_GoldenPinUp'].sum()):,}")

    # V3.2 定義
    V32 = {
        "L17": {"c":(df["Country"]=="HK")&df["goldDn_filtered"]&(df["tier"]=="S+⚡⚡")&(df["RSI"]<45)&(df["blueup_14d"]>=2), "d":"LONG", "def":"Cap+Tier⚡⚡+RSI<45+Blue14d≥2"},
        "L16": {"c":(df["Country"]=="HK")&df["goldDn_filtered"]&(df["tier"].isin(["S+⚡","S+⚡⚡"]))&(df["RSI"]<45)&(df["w2s_7d"]>=1), "d":"LONG", "def":"Cap+Tier≥S+⚡+RSI<45+W2S7d≥1"},
        "L06": {"c":(df["Country"]=="HK")&df["is_GoldenPinDown"]&df["is_WeakToStrong"], "d":"LONG", "def":"GoldDn+W2S"},
        "L04": {"c":(df["Country"]=="HK")&df["is_GoldenPinDown"]&(df["GoldGateOnAlgo1"]=="Y"), "d":"LONG", "def":"GoldDn+GoldGate1"},
        "L03": {"c":(df["Country"]=="HK")&df["goldDn_filtered"]&(df["RSI"]<45)&(df["w2s_7d"]>=1), "d":"LONG", "def":"Cap+RSI<45+W2S7d≥1"},
        "S02": {"c":(df["Country"]=="HK")&df["is_GoldenPinUp"]&(df["blueup_30d"]<=1)&(df["RSI"]>60)&(df["drop_30d_pct"]>0.15), "d":"SHO", "def":"Blue30d≤1+RSI>60+Drop>15%"},
        "S01": {"c":(df["Country"]=="HK")&df["is_GoldenPinUp"]&(df["blueup_7d"]==0)&(df["RSI"]>65), "d":"SHO", "def":"Blue7d=0+RSI>65"},
        "S11": {"c":(df["Country"]=="HK")&df["is_GoldenPinUp"]&(df["blueup_14d"]==0)&(df["RSI"]>60)&(df["drop_30d_pct"]>0.10), "d":"SHO", "def":"Blue14d=0+RSI>60+Drop>10%"},
        "US01":{"c":(df["Country"]=="US")&df["is_GoldenPinDown"]&(df["tier"]=="S+⚡⚡"), "d":"LONG", "def":"US GoldDn+Tier⚡⚡"},
        "US02":{"c":(df["Country"]=="US")&df["is_GoldenPinDown"]&df["is_WeakToStrong"], "d":"LONG", "def":"US GoldDn+W2S"},
        "US03":{"c":(df["Country"]=="US")&df["is_GoldenPinDown"]&(df["GoldGateOnAlgo1"]=="Y"), "d":"LONG", "def":"US GoldDn+GoldGate1"},
        "US04":{"c":(df["Country"]=="US")&df["is_GoldenPinUp"]&(df["blueup_14d"]==0)&(df["RSI"]>60), "d":"SHO", "def":"US Blue14d=0+RSI>60"},
        "US05":{"c":(df["Country"]=="US")&df["is_GoldenPinUp"]&(df["blueup_14d"]==0), "d":"SHO", "def":"US Blue14d=0"},
        "US06":{"c":(df["Country"]=="US")&df["is_GoldenPinUp"]&(df["blueup_7d"]==0)&(df["RSI"]>55), "d":"SHO", "def":"US Blue7d=0+RSI>55"},
    }
    
    # V3 舊定義 (對比用)
    V3_OLD = {
        "L17": {"c":(df["Country"]=="HK")&df["goldDn_filtered"]&(df["tier"]=="S+⚡⚡")&(df["blueup_7d"]>=3), "d":"LONG", "def":"Cap+Tier⚡⚡+Blue7d≥3"},
        "L16": {"c":(df["Country"]=="HK")&df["goldDn_filtered"]&(df["tier"].isin(["S+⚡","S+⚡⚡"]))&(df["blueup_7d"]>=2), "d":"LONG", "def":"Cap+Tier⚡/⚡⚡+Blue7d≥2"},
        "L03": {"c":(df["Country"]=="HK")&df["goldDn_filtered"]&(df["RSI"]<40), "d":"LONG", "def":"Cap+RSI<40"},
        "S01": {"c":(df["Country"]=="HK")&df["is_GoldenPinUp"]&(df["blueup_7d"]==0), "d":"SHO", "def":"Blue7d=0"},
        "S11": {"c":(df["Country"]=="HK")&df["is_GoldenPinUp"]&(df["drop_30d_pct"]>0.10), "d":"SHO", "def":"Drop>10%"},
        "US05":{"c":(df["Country"]=="US")&df["is_GoldenPinUp"]&(df["blueup_7d"]==0), "d":"SHO", "def":"US Blue7d=0"},
    }

    sep = "="*80
    print(f"\n{sep}")
    print("📊 V3.2 正式回測結果")
    print(sep)
    
    print(f"\n   Ind   方向   定義                               │  5日持有         │  7日持有         │  14日持有")
    print(f"   {'─'*105}")
    
    for name in ["L17","L16","L06","L04","L03","S02","S01","S11","US01","US02","US03","US04","US05","US06"]:
        ind = V32[name]
        nsig = int(ind["c"].sum())
        row = f"   {name:<5} {ind['d']:<5} {ind['def']:<35} │"
        for h in [5,7,14]:
            bt = vbt(df, ind["c"], ind["d"], h, 3)
            if bt:
                f = "🔥" if bt["wr"]>=0.65 else ""
                row += f" n={bt['n']:>3} {bt['wr']:.0%}{f} PnL={bt['pnl']:+.1f}%│"
            else:
                row += f"    N/A               │"
        print(row)
    
    # V3 vs V3.2 對比
    print(f"\n{sep}")
    print("📊 V3 舊 vs V3.2 新 對比 (5日持有)")
    print(sep)
    print(f"   Ind   │    V3 舊              │    V3.2 新              │  Δ勝率  │  ΔPnL")
    print(f"   {'─'*85}")
    
    for name in ["L17","L16","L03","S01","S11","US05"]:
        if name not in V3_OLD: continue
        old = V3_OLD[name]; new = V32[name]
        ob = vbt(df, old["c"], old["d"], 5, 3)
        nb = vbt(df, new["c"], new["d"], 5, 3)
        if ob and nb:
            wd = nb["wr"]-ob["wr"]; pd = nb["pnl"]-ob["pnl"]
            print(f"   {name:<5} │ n={ob['n']:>3} WR={ob['wr']:.0%} PnL={ob['pnl']:+.1f}% │ n={nb['n']:>3} WR={nb['wr']:.0%} PnL={nb['pnl']:+.1f}% │ {wd:+.0%}  │ {pd:+.1f}%")
        elif nb:
            print(f"   {name:<5} │    N/A               │ n={nb['n']:>3} WR={nb['wr']:.0%} PnL={nb['pnl']:+.1f}% │  🆕    │  🆕")
    
    # 總結
    print(f"\n{sep}")
    print("📝 V3.2 回測總結")
    print(sep)
    l_wrs, s_wrs = [], []
    for n, ind in V32.items():
        bt = vbt(df, ind["c"], ind["d"], 5, 3)
        if bt:
            if ind["d"]=="LONG": l_wrs.append(bt["wr"])
            else: s_wrs.append(bt["wr"])
    if l_wrs: print(f"   LONG 平均勝率：{np.mean(l_wrs):.1%}")
    if s_wrs: print(f"   SHO  平均勝率：{np.mean(s_wrs):.1%}")
    
    print(f"\n   ✅ V3.2 更新完成")
