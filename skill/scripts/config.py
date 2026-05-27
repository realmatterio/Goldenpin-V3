#!/usr/bin/env python3
"""
Golden Pin Config — V3 系統配置參數
"""

from pathlib import Path

# ── Data Paths ────────────────────────────────────────────────────────────────

DATA_DIR = Path("/Users/ttse/.openclaw/workspace-stock-goldenpin/data/Golden Pin Stockbot - OpenClaw")
OUTPUT_DIR = Path(__file__).parent.parent / "output"

# ── V3 System Parameters (from Preface_0000) ─────────────────────────────────

# Capitulation Filter
CAPITULATION_MAX_DROP_30D = 0.25       # 30 日最大跌幅 < 25%
BLUEUP_MIN_DAYS = 7                     # 7 日 BluePinUp 或 W2S 證據

# Tier Enhancement
TIER_THRESHOLDS = {
    4: "S+⚡⚡",    # 最強
    3: "S+⚡",      # 強
    2: "S+",        # 中強
    1: "S",         # base
}
TIER_WINDOW = 30  # 30 日滾動窗口

# 3-Tranche Limit Orders
TRANCHE_PCT = [0.30, 0.40, 0.30]  # 即時 / P50 / P25

# 14 Validated Indicators (V3)
LONG_HK = ["L17", "L16", "L06", "L04", "L03"]   # 5 港股 LONG
SHO_HK  = ["S02", "S01", "S11"]                    # 3 港股 SHO
LONG_US = ["US01", "US02", "US03"]                  # 3 美股 LONG
SHO_US  = ["US04", "US05", "US06"]                  # 3 美股 SHO
ALL_INDICATORS = LONG_HK + SHO_HK + LONG_US + SHO_US  # 14 total

# 8 大紀律 (from Preface_0000)
DISCIPLINES = {
    "no_sho_before_earnings_7d": True,   # 業績前 7 日不開 SHO
    "max_position_pct": 0.05,             # 單一倉位 ≤ 5%
}

# Backtest defaults
BACKTEST_HOLD_DAYS = 5
BACKTEST_TRANCHE = True

# CSV columns mapping
SIGNAL_COLUMNS = {
    "GoldenPinDown": "GoldDn",
    "GoldenPinUp": "GoldUp",
    "BluePinUp": "BlueUp",
    "BluePinDown": "BlueDown",
    "WeakToStrong": "W2S",
    "StrongToWeak": "S2W",
    "GreyPinDown": "GreyDn",
}

PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Adj.Close", "Volume"]
