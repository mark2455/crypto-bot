"""
[루프 13회차] Schaff Trend Cycle (STC) — MACD 라인에 스토캐스틱을 두 번 적용해
더 빠르게 반응하도록 만든 지표. MACD도 스토캐스틱도 아닌 둘의 결합이라 새로운 구성.

macd = EMA(종가,23) - EMA(종가,50)
%K1 = 스토캐스틱(macd, N=10), %D1 = EMA(%K1,3)
%K2 = 스토캐스틱(%D1, N=10), STC = EMA(%K2,3)   범위 0~100

실행:  ~/crypto-bot/venv/bin/python stc_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 10


def stoch_of(series, n=N):
    s = pd.Series(series)
    lo = s.rolling(n).min()
    hi = s.rolling(n).max()
    rng = hi - lo
    return (100 * (s - lo) / rng).fillna(50).to_numpy()


def stc(close, n=N):
    macd = pd.Series(close).ewm(span=23, adjust=False).mean() - pd.Series(close).ewm(span=50, adjust=False).mean()
    k1 = stoch_of(macd.to_numpy(), n)
    d1 = pd.Series(k1).ewm(span=3, adjust=False).mean()
    k2 = stoch_of(d1.to_numpy(), n)
    out = pd.Series(k2).ewm(span=3, adjust=False).mean()
    return out.to_numpy()


def run(df, buy_th=25, exit_th=75, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    s = stc(close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 100 - buy_th, 100 - exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 260
    nlen = len(close)
    while i < nlen:
        if side != 0:
            held += 1
            if side == 1 and (s[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (s[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if s[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and s[i] > sell_th and close[i] < ma200[i]:
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
        print(f"\n=== STC buy<25 exit>75 — {mode_name}, 9코인 4년4국면 ===")
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
