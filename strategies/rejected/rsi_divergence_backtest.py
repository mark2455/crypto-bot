"""
[루프 13회차-2] RSI 다이버전스 — 임계값 돌파가 아니라 '가격 vs RSI 패턴 불일치'를 탐지.
강세다이버전스: 가격은 신저점을 갱신하는데 RSI는 신저점을 못 갱신(하락모멘텀 약화) → 반전기대
약세다이버전스: 가격은 신고점 갱신하는데 RSI는 신고점 못갱신 → 반전기대

lookahead 방지: 피벗은 항상 index<=현재-PIVOT_K 인 확정된 것만 사용.

실행:  ~/crypto-bot/venv/bin/python rsi_divergence_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv
from indicator_analysis import rsi
from chart_patterns import find_pivots, PIVOT_K

FEE = 0.0004
MAX_HOLD = 100


def run(df, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    r = rsi(close, 14)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    hp, lp = find_pivots(high, low)

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 220
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            exit_now = (side == 1 and r[i] > 60) or (side == -1 and r[i] < 40) or held >= MAX_HOLD
            if exit_now:
                net = (close[i] / entry - 1 if side == 1 else 1 - close[i] / entry) - 2 * FEE
                trades.append(net); side = 0
            i += 1; continue

        # 확정된 피벗 중 최근 2개 비교
        recent_lp = [j for j in lp if j <= i - PIVOT_K]
        recent_hp = [j for j in hp if j <= i - PIVOT_K]

        bullish_div = False
        if len(recent_lp) >= 2:
            l1, l2 = recent_lp[-2], recent_lp[-1]
            if low[l2] < low[l1] and r[l2] > r[l1] and (i - l2) <= 20:
                bullish_div = True

        bearish_div = False
        if len(recent_hp) >= 2:
            h1, h2 = recent_hp[-2], recent_hp[-1]
            if high[h2] > high[h1] and r[h2] < r[h1] and (i - h2) <= 20:
                bearish_div = True

        if bullish_div and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and bearish_div and close[i] < ma200[i]:
            side, entry, held = -1, close[i], 0
        i += 1

    if not trades:
        return {"trades": 0, "return": 0.0, "win_rate": 0.0}
    t = np.array(trades)
    return {"trades": len(t), "return": (np.prod(1 + t) - 1) * 100, "win_rate": (t > 0).mean() * 100}


COINS = ["DOTUSDT", "LTCUSDT", "LINKUSDT", "XRPUSDT", "ETCUSDT",
         "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
PERIODS = [("2022-07-30", "2023-07-30"), ("2023-07-30", "2024-07-30"),
           ("2024-07-30", "2025-07-30"), ("2025-07-30", "2026-07-29")]


def main():
    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== RSI 다이버전스 — {mode_name}, 9코인 4년4국면 ===")
        for coin in COINS:
            df = load_candles_csv(f"data/{coin}_1h_4y.csv")
            pos = 0; yearly = []
            for start, end in PERIODS:
                mask = (df["time"] >= start) & (df["time"] < end)
                d = df[mask].reset_index(drop=True)
                if len(d) < 300:
                    continue
                r = run(d, allow_short=allow_short)
                yearly.append(r["return"])
                if r["return"] > 0:
                    pos += 1
            r_full = run(df, allow_short=allow_short)
            mark = "★" if pos == 4 else ""
            ys = "  ".join(f"{y:+7.1f}%" for y in yearly)
            print(f"  {coin.replace('USDT',''):6} {ys}  4년합계 {r_full['return']:+8.2f}%  {pos}/4 {mark}")


if __name__ == "__main__":
    main()
