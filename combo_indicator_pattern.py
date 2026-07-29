"""
지표(Connors RSI, 확정 신호) + 패턴(삼각수렴) 조합 검증 — 9개 코인(4년치) 전체.

모드 3가지:
  - connors : 확정 전략 단독 (기준선)
  - and     : Connors 신호와 삼각수렴 신호가 '같은 방향으로 동시에' 나올 때만 진입 (더 엄격)
  - or      : 둘 중 '하나라도' 나오면 진입 (Connors 우선, 없으면 삼각수렴)
청산은 전부 Connors 방식(CRSI 회복 또는 MAX_HOLD)을 그대로 사용.

실행:  ~/crypto-bot/venv/bin/python combo_indicator_pattern.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv
from connors_rsi_backtest import connors_rsi
from chart_patterns import find_pivots, signal_triangle, PIVOT_K, LOOKBACK

FEE = 0.0004
MAX_HOLD = 100
BUY_TH, EXIT_TH = 10, 50
SELL_TH, COVER_TH = 100 - BUY_TH, 100 - EXIT_TH

COINS = ["DOTUSDT", "LTCUSDT", "LINKUSDT", "XRPUSDT", "ETCUSDT",
         "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]


def run(df, mode="connors"):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    crsi = connors_rsi(close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    hp, lp = find_pivots(high, low)

    trades = []
    side = 0; entry = 0.0; held = 0
    i = max(250, LOOKBACK + PIVOT_K + 1)
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            if side == 1 and (crsi[i] > EXIT_TH or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (crsi[i] < COVER_TH or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        c_sig = 0
        if crsi[i] < BUY_TH and close[i] > ma200[i]:
            c_sig = 1
        elif crsi[i] > SELL_TH and close[i] < ma200[i]:
            c_sig = -1

        sig = 0
        if mode == "connors":
            sig = c_sig
        else:
            t_sig = signal_triangle(i, high, low, close, hp, lp)
            if mode == "and":
                sig = c_sig if (c_sig != 0 and c_sig == t_sig) else 0
            elif mode == "or":
                sig = c_sig if c_sig != 0 else t_sig

        if sig != 0:
            side, entry, held = sig, close[i], 0
        i += 1

    if not trades:
        return {"trades": 0, "return": 0.0}
    t = np.array(trades)
    return {"trades": len(t), "return": (np.prod(1 + t) - 1) * 100}


def main():
    periods = [
        ("2022-07-30", "2023-07-30"), ("2023-07-30", "2024-07-30"),
        ("2024-07-30", "2025-07-30"), ("2025-07-30", "2026-07-29"),
    ]
    print(f"=== Connors RSI 단독 vs +삼각수렴(AND) vs +삼각수렴(OR) — 9개 코인 4년 ===\n")
    print(f"{'코인':6} {'모드':10} {'4년수익':>10} {'플러스연도':>8}")
    print("-" * 42)
    for coin in COINS:
        df = load_candles_csv(f"data/{coin}_1h_4y.csv")
        for mode in ["connors", "and", "or"]:
            pos = 0
            for start, end in periods:
                mask = (df["time"] >= start) & (df["time"] < end)
                d = df[mask].reset_index(drop=True)
                if len(d) < 300:
                    continue
                r = run(d, mode)
                if r["return"] > 0:
                    pos += 1
            r_full = run(df, mode)
            mark = "★" if pos == 4 else ""
            print(f"{coin.replace('USDT',''):6} {mode:10} {r_full['return']:+9.2f}%   {pos}/4  {mark}")
        print()


if __name__ == "__main__":
    main()
