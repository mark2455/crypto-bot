"""
[루프 9회차] Awesome Oscillator (Bill Williams) — 중간가(고+저)/2 의 단기(5)/장기(34) 이동평균 차이.
MACD와 비슷한 개념이나 종가 대신 중간가를 쓰고 단순이동평균 사용.

AO = SMA(중간가,5) - SMA(중간가,34)
%AO = AO / 종가 * 100  (코인간 비교용 정규화)

실행:  ~/crypto-bot/venv/bin/python awesome_osc_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def ao_pct(high, low, close):
    mid = (high + low) / 2
    fast = pd.Series(mid).rolling(5).mean()
    slow = pd.Series(mid).rolling(34).mean()
    ao = (fast - slow).to_numpy()
    return ao / close * 100


def run(df, buy_th=-1.0, exit_th=0.0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    a = ao_pct(high, low, close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            if side == 1 and (a[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (a[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if a[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and a[i] > sell_th and close[i] < ma200[i]:
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
    a0 = ao_pct(df0["high"].to_numpy(float), df0["low"].to_numpy(float), df0["close"].to_numpy(float))
    print(f"[분포확인] BTC %AO: 1%={np.nanpercentile(a0,1):.2f} 5%={np.nanpercentile(a0,5):.2f} "
          f"95%={np.nanpercentile(a0,95):.2f} 99%={np.nanpercentile(a0,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== Awesome Osc %AO buy<-1.0 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
