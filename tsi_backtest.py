"""
[루프 5회차] True Strength Index (TSI) — 모멘텀을 EMA로 두 번 평활화(이중평활)한 오실레이터.
CMO(평활화 없음)와 정반대 극단 — 노이즈를 크게 줄인 버전. 범위 대략 -100~100.

momentum = close - close[1]
1차평활(r=25) → 2차평활(s=13)  (모멘텀 자체와 |모멘텀| 둘 다)
TSI = 100 * 이중평활(모멘텀) / 이중평활(|모멘텀|)

실행:  ~/crypto-bot/venv/bin/python tsi_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def tsi(close, r=25, s=13):
    mom = np.diff(close, prepend=close[0])
    s1 = pd.Series(mom).ewm(span=r, adjust=False).mean()
    s2 = s1.ewm(span=s, adjust=False).mean()
    a1 = pd.Series(np.abs(mom)).ewm(span=r, adjust=False).mean()
    a2 = a1.ewm(span=s, adjust=False).mean()
    return (100 * s2 / a2).to_numpy()


def run(df, buy_th=-25, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    t = tsi(close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            if side == 1 and (t[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (t[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if t[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and t[i] > sell_th and close[i] < ma200[i]:
            side, entry, held = -1, close[i], 0
        i += 1

    if not trades:
        return {"trades": 0, "return": 0.0, "win_rate": 0.0}
    tr = np.array(trades)
    return {"trades": len(tr), "return": (np.prod(1 + tr) - 1) * 100, "win_rate": (tr > 0).mean() * 100}


COINS = ["DOTUSDT", "LTCUSDT", "LINKUSDT", "XRPUSDT", "ETCUSDT",
         "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
PERIODS = [("2022-07-30", "2023-07-30"), ("2023-07-30", "2024-07-30"),
           ("2024-07-30", "2025-07-30"), ("2025-07-30", "2026-07-29")]


def main():
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    t0 = tsi(df0["close"].to_numpy(dtype=float))
    print(f"[분포확인] BTC TSI: min={t0.min():.1f} max={t0.max():.1f} "
          f"1%={np.percentile(t0,1):.1f} 5%={np.percentile(t0,5):.1f} "
          f"95%={np.percentile(t0,95):.1f} 99%={np.percentile(t0,99):.1f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== TSI buy<-25 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
