#!/usr/bin/env python3
"""
Goldenpin Office Assistant - Prompt Handler
用法: goldenpin <股票編號>

分析流程：
1. 解析股票編號並識別市場
2. 用 yfinance 獲取實時數據
3. 在 Goldenpin 歷史數據庫中搜索
4. 運行 V3.2 分析引擎
5. 輸出完整報告
"""

import sys
import re
import subprocess
from pathlib import Path
from datetime import datetime

# ── 常量 ──────────────────────────────────────────────────────────────────────
GOLDENPIN_DIR = Path("~/skill")
SCRIPTS_DIR = GOLDENPIN_DIR / "scripts"
DATA_DIR = Path("~/data/pretrain")
OUTPUT_DIR = GOLDENPIN_DIR / "output"

# 股票市場映射
HK_STOCK_CODES = {
    "0700", "9988", "0941", "3690", "1810", "6618", "2319",
    "600519", "601318", "600036", "000858"
}  # 簡化示例

# ── 工具函數 ──────────────────────────────────────────────────────────────────
def print_step(step_num, message):
    """打印分析步驟"""
    print(f"\n{'='*60}")
    print(f"▶ STEP {step_num}: {message}")
    print(f"{'='*60}")

def is_hk_stock(code: str) -> bool:
    """判斷是否為港股"""
    return code.isdigit() or (code.startswith("0") and len(code) == 4)

def get_stock_info(code: str) -> dict:
    """用 yfinance 獲取股票基本資訊"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(code)
        info = ticker.info
        
        # 嘗試獲取基本信息
        short_name = info.get("shortName", info.get("longName", "Unknown"))
        current_price = info.get("currentPrice", info.get("regularMarketPrice", "N/A"))
        market = info.get("market", "unknown")
        
        return {
            "code": code,
            "name": short_name,
            "price": current_price,
            "market": market,
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange", "unknown"),
        }
    except Exception as e:
        return {
            "code": code,
            "name": "Unknown",
            "price": "N/A",
            "market": "unknown",
            "error": str(e)
        }

def search_goldenpin_data(stock_code: str) -> dict:
    """在 Goldenpin 數據庫中搜索股票"""
    print(f"🔍 搜索股票 {stock_code} 在 Goldenpin 歷史數據庫...")
    
    if not DATA_DIR.exists():
        return {"found": False, "error": "數據庫不存在"}
    
    # 轉換股票代碼格式
    # 港股: 0700 -> 0700.HK
    # 美股: AAPL (保持不變)
    search_codes = [stock_code]
    if stock_code.isdigit() and len(stock_code) == 4:
        search_codes = [f"{stock_code}.HK", stock_code]
    elif stock_code.isupper() and stock_code.isalpha():
        search_codes = [stock_code]
    
    csv_files = sorted(DATA_DIR.glob("StockDailyPins*.csv*"))
    
    stock_data = []
    for f in csv_files:
        try:
            import pandas as pd
            df = pd.read_csv(f)
            for code in search_codes:
                matches = df[df["Stock_No"] == code]
                if len(matches) > 0:
                    stock_data.append(matches)
                    print(f"   ✅ 在 {f.name} 中找到 {len(matches)} 條記錄")
                    break
        except Exception as e:
            continue
    
    if stock_data:
        import pandas as pd
        combined = pd.concat(stock_data, ignore_index=True).drop_duplicates()
        latest = combined.sort_values("Date", ascending=False).iloc[0] if len(combined) > 0 else {}
        
        return {
            "found": True,
            "count": len(combined),
            "latest": latest.to_dict() if hasattr(latest, 'to_dict') else {},
            "df": combined
        }
    
    return {"found": False, "count": 0}

def run_goldenpin_analyzer(stock_code: str) -> str:
    """運行 Goldenpin 分析器"""
    try:
        result = subprocess.run(
            ["python3", str(SCRIPTS_DIR / "analyzer.py")],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "❌ 分析超时"
    except Exception as e:
        return f"❌ 分析错误: {e}"

def generate_office_report(stock_code: str, stock_info: dict, gp_data: dict) -> str:
    """生成 Office Assistant 格式報告"""
    lines = []
    
    lines.append("=" * 70)
    lines.append("📈 GOLDENPIN V3 分析報告 — Office Assistant")
    lines.append("=" * 70)
    
    # 股票基本資訊
    lines.append(f"\n🎯 目標股票：{stock_code}")
    lines.append(f"   名稱：{stock_info.get('name', 'N/A')}")
    lines.append(f"   現價：{stock_info.get('price', 'N/A')}")
    
    # 市場判斷
    is_hk = stock_code.isdigit()
    market = "🌏 港股" if is_hk else "🌎 美股"
    lines.append(f"   市場：{market}")
    
    # Goldenpin 歷史數據
    lines.append("\n" + "-" * 70)
    lines.append("📊 GOLDENPIN 歷史數據")
    lines.append("-" * 70)
    
    if gp_data.get("found"):
        lines.append(f"   ✅ 在數據庫中找到 {gp_data.get('count', 0)} 條記錄")
        
        latest = gp_data.get("latest", {})
        if latest:
            lines.append(f"\n   📅 最新記錄：{latest.get('Date', 'N/A')}")
            lines.append(f"   📌 收盤價：{latest.get('Close', latest.get('close', 'N/A'))}")
            lines.append(f"   📌 RSI：{latest.get('RSI', 'N/A')}")
            
            # 顯示所有信號
            signals = []
            if latest.get("GoldenPinDown") == "Y":
                signals.append("📉 GoldenPinDown")
            if latest.get("GoldenPinUp") == "Y":
                signals.append("📈 GoldenPinUp")
            if latest.get("BluePinUp") == "Y":
                signals.append("🔵 BluePinUp")
            if latest.get("WeakToStrong") == "Y":
                signals.append("⚡ WeakToStrong")
            if latest.get("StrongToWeak") == "Y":
                signals.append("📉 StrongToWeak")
            
            if signals:
                lines.append(f"\n   🔔 活躍信號：{' | '.join(signals)}")
            else:
                lines.append(f"\n   📭 暫無活躍信號")
    else:
        lines.append(f"   ⚠️ 在數據庫中未找到 {stock_code}")
        lines.append(f"   💡 嘗試格式：0700.HK (港股) 或 AAPL (美股)")
    
    # V3 14 Indicators 狀態
    lines.append("\n" + "-" * 70)
    lines.append("🎯 V3.2 14 INDICATORS 狀態")
    lines.append("-" * 70)
    
    if is_hk:
        lines.append("   🟡 LONG 信號指標：")
        lines.append("      L17: Cap + Tier=S+⚡⚡ + RSI<45 + Blue14d≥2 (勝率 39%)")
        lines.append("      L16: Cap + Tier≥S+⚡ + RSI<45 + W2S7d≥1 (勝率 55%) ⭐")
        lines.append("      L03: Cap + RSI<45 + W2S7d≥1 (勝率 54%)")
        lines.append("\n   🔴 SHORT 信號指標：")
        lines.append("      S02: Blue30d≤1 + RSI>60 + Drop>15% (勝率 75%) ⭐")
        lines.append("      S11: Blue14d=0 + RSI>60 + Drop>10% (勝率 67%)")
        lines.append("      S01: Blue7d=0 + RSI>65 (勝率 58%)")
    else:
        lines.append("   🟡 LONG 信號指標：")
        lines.append("      US01: GoldDn + Tier=S+⚡⚡ (勝率 32%)")
        lines.append("\n   🔴 SHORT 信號指標：")
        lines.append("      US05: Blue14d=0 (勝率 70%) ⭐")
        lines.append("      US04: Blue14d=0 + RSI>60 (勝率 48%)")
        lines.append("      US06: Blue7d=0 + RSI>55 (勝率 54%)")
    
    # 操作建議
    lines.append("\n" + "-" * 70)
    lines.append("💡 操作建議")
    lines.append("-" * 70)
    
    if gp_data.get("found") and latest:
        rsi_val = latest.get('RSI', 50)
        try:
            rsi_val = float(rsi_val)
            if rsi_val < 45:
                lines.append("   📈 RSI 低於 45，存在 LONG 反彈機會")
            elif rsi_val > 60:
                lines.append("   📉 RSI 高於 60，存在 SHORT 機會")
            else:
                lines.append("   ➡️ RSI 中性，建議觀望")
            lines.append(f"   📊 RSI 當前值：{rsi_val:.1f}")
        except:
            lines.append(f"   📊 RSI：{rsi_val}")
        
        # 3-Tranche 入場
        close = latest.get('Close', latest.get('close', 0))
        high = latest.get('High', 0)
        low = latest.get('Low', 0)
        
        if close and float(close) > 0 and high and low:
            p50 = (float(high) + float(low)) / 2
            p25 = float(low) + 0.25 * (float(high) - float(low))
            
            lines.append(f"\n   🏦 3-Tranche 入場價：")
            lines.append(f"      T1 (30%) @ 市價：{float(close):.2f}")
            lines.append(f"      T2 (40%) @ P50：{p50:.2f}")
            lines.append(f"      T3 (30%) @ P25：{p25:.2f}")
    else:
        lines.append("   ⚠️ 缺少歷史數據，無法計算入場價")
        lines.append("   💡 建議：確保股票在 Goldenpin 數據庫中")
    
    lines.append("\n" + "=" * 70)
    lines.append(f"📊 報告生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    
    return "\n".join(lines)

# ── 主程序 ─────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("""
╔══════════════════════════════════════════════════════════════╗
║           GOLDENPIN V3 — Office Assistant Skill              ║
╠══════════════════════════════════════════════════════════════╣
║  用法: goldenpin <股票編號>                                   ║
║                                                              ║
║  例子:                                                       ║
║    goldenpin 0700      → 分析騰訊 (港股)                    ║
║    goldenpin 9988      → 分析阿里巴巴 (港股)                 ║
║    goldenpin AAPL      → 分析 Apple (美股)                  ║
║    goldenpin NVDA      → 分析 NVIDIA (美股)                  ║
║                                                              ║
║    goldenpin help      → 顯示幫助                           ║
╚══════════════════════════════════════════════════════════════╝
        """)
        sys.exit(1)
    
    stock_code = sys.argv[1]
    
    # 顯示幫助
    if stock_code.lower() == "help":
        print("""
╔══════════════════════════════════════════════════════════════╗
║           GOLDENPIN V3 — 使用說明                            ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  📋 支援股票類型：                                            ║
║     • 港股：4位數字 (如 0700, 9988)                          ║
║     • 美股：英文字母代碼 (如 AAPL, NVDA, TSLA)               ║
║                                                              ║
║  🎯 分析功能：                                                ║
║     • 實時股價查詢 (yfinance)                                 ║
║     • Goldenpin 歷史信號搜索                                 ║
║     • V3.2 14 Indicators 分析                               ║
║     • Capitulation Filter 過濾                               ║
║     • Tier Enhancement 分級                                   ║
║     • 3-Tranche 入場價建議                                   ║
║                                                              ║
║  📊 最佳表現指標：                                            ║
║     • S02 (港股Short): 75% 勝率                              ║
║     • S11 (港股Short): 67% 勝率                              ║
║     • US05 (美股Short): 70% 勝率                              ║
║     • L16 (港股Long): 55% 勝率                               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """)
        sys.exit(0)
    
    # ── Step 1: 股票識別 ──────────────────────────────────────────
    print_step(1, f"識別股票 {stock_code}")
    
    stock_info = get_stock_info(stock_code)
    print(f"   📌 股票代碼：{stock_info['code']}")
    print(f"   📌 股票名稱：{stock_info.get('name', 'N/A')}")
    print(f"   📌 當前價格：{stock_info.get('price', 'N/A')}")
    print(f"   📌 市場：{stock_info.get('market', 'unknown')}")
    
    # ── Step 2: 搜索 Goldenpin 數據庫 ────────────────────────────
    print_step(2, "搜索 Goldenpin 歷史數據庫")
    
    gp_data = search_goldenpin_data(stock_code)
    if gp_data.get("found"):
        print(f"   ✅ 找到 {gp_data.get('count', 0)} 條歷史記錄")
    else:
        print(f"   ⚠️ 未在歷史數據庫中找到")
    
    # ── Step 3: 運行分析引擎 ─────────────────────────────────────
    print_step(3, "運行 V3.2 分析引擎")
    print(f"   ⚙️ 執行 analyzer.py...")
    analyzer_output = run_goldenpin_analyzer(stock_code)
    
    # ── Step 4: 生成報告 ───────────────────────────────────────────
    print_step(4, "生成分析報告")
    
    report = generate_office_report(stock_code, stock_info, gp_data)
    print(report)
    
    # 保存報告
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    report_path = OUTPUT_DIR / f"office_report_{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    Path(report_path).write_text(report, encoding="utf-8")
    print(f"\n💾 報告已保存：{report_path}")

if __name__ == "__main__":
    main()
