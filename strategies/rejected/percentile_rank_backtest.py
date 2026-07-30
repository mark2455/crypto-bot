"""
[루프 52회차] Percentile Rank — Donchian %Position(최고가/최저가 딱 두 점 기준)과 달리,
최근 N봉 종가 "전체 분포" 안에서 지금 종가가 몇 퍼센타일인지를 본다 — 중간에 낀 값들의
밀도까지 반영해서 극단적 이상치(wick) 한두 개에 덜 휘둘림.

PercentileRank[i] = (최근N봉 종가 중 지금 종가보다 작거나 같은 값의 비율) * 100   (0~100 유계)

실행:  ~/crypto-bot/venv/bin/python percentile_rank_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 50


def percentile_rank(close, n=N):
    s = pd.Series(close, dtype=float)
    return s.rolling(n).apply(lambda w: (w <= w[-1]).mean() * 100, raw=True).to_numpy()


def run(df, buy_th=10, exit_th=50, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    p = percentile_rank(close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 100 - buy_th, 100 - exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = n + 210
    m = len(close)
    while i < m:
        if np.isnan(p[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (p[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (p[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if p[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and p[i] > sell_th and close[i] < ma200[i]:
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
        print(f"\n=== Percentile Rank buy<10 exit>50 — {mode_name}, 9코인 4년4국면 ===")
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
