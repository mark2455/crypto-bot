"""
[루프 14회차] Hull Moving Average(HMA) 대비 가격 괴리% — WMA(가중이동평균)를 두 번 다른
기간으로 계산해 빼고 다시 평활화하는 트릭으로 지연을 크게 줄인 이동평균. EMA 기반
지표들(Elder Ray 등)과 평활화 메커니즘 자체가 다름.

WMA_half = WMA(종가, N/2), WMA_full = WMA(종가, N)
raw = 2*WMA_half - WMA_full
HMA = WMA(raw, sqrt(N))
%괴리 = (종가-HMA)/종가*100

실행:  ~/crypto-bot/venv/bin/python hma_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 20


def wma(x, n):
    weights = np.arange(1, n + 1)
    return pd.Series(x).rolling(n).apply(lambda w: np.dot(w, weights) / weights.sum(), raw=True).to_numpy()


def hma_dist_pct(close, n=N):
    half = max(n // 2, 1)
    sqrt_n = max(int(round(np.sqrt(n))), 1)
    wma_half = wma(close, half)
    wma_full = wma(close, n)
    raw = 2 * wma_half - wma_full
    hma = wma(raw, sqrt_n)
    return (close - hma) / close * 100


def run(df, buy_th=-3, exit_th=0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    d = hma_dist_pct(close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    nlen = len(close)
    while i < nlen:
        if side != 0:
            held += 1
            if side == 1 and (d[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (d[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if d[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and d[i] > sell_th and close[i] < ma200[i]:
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
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    d0 = hma_dist_pct(df0["close"].to_numpy(dtype=float))
    d0v = d0[~np.isnan(d0)]
    print(f"[분포확인] BTC %HMA괴리: 1%={np.percentile(d0v,1):.2f} 5%={np.percentile(d0v,5):.2f} "
          f"95%={np.percentile(d0v,95):.2f} 99%={np.percentile(d0v,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== HMA 괴리% buy<-3 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
