"""
[루프 9회차-2] Balance of Power (BOP) — 한 봉 안에서 매수세/매도세를 직접 측정.
RVI(대칭가중평활)나 Elder Ray(추세EMA대비)와 달리 가장 단순한 원시 형태.

BOP = (종가-시가)/(고가-저가)   범위 -1~1, N기간 단순평균으로 평활.

실행:  ~/crypto-bot/venv/bin/python bop_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 14


def bop_smoothed(open_, high, low, close, n=N):
    rng = high - low
    bop = np.divide(close - open_, rng, out=np.zeros_like(rng), where=rng != 0)
    return pd.Series(bop).rolling(n).mean().to_numpy()


def run(df, buy_th=-0.3, exit_th=0.0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    open_ = df["open"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    b = bop_smoothed(open_, high, low, close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            if side == 1 and (b[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (b[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if b[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and b[i] > sell_th and close[i] < ma200[i]:
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
    b0 = bop_smoothed(df0["open"].to_numpy(float), df0["high"].to_numpy(float),
                       df0["low"].to_numpy(float), df0["close"].to_numpy(float))
    print(f"[분포확인] BTC BOP(14): 1%={np.nanpercentile(b0,1):.2f} 5%={np.nanpercentile(b0,5):.2f} "
          f"95%={np.nanpercentile(b0,95):.2f} 99%={np.nanpercentile(b0,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== BOP(14) buy<-0.3 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
