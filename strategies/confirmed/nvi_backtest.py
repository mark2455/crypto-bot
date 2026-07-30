"""
[루프 17회차] Negative Volume Index (NVI) — '거래량이 줄어든 날의 가격변화만' 누적.
OBV/MFI/Chaikin/Klinger 전부 가격변화나 가격범위에 거래량을 곱하는 방식이었다면,
NVI는 정반대로 '거래량 자체의 증감'을 조건으로 가격변화를 선택적으로 누적하는
전혀 다른 발상(스마트머니 이론: 거래량 적은 날의 움직임이 더 유의미하다는 가설).

NVI[i] = NVI[i-1] * (종가[i]/종가[i-1])  거래량[i] < 거래량[i-1] 일 때만, 아니면 그대로.
z = 롤링 정규화

실행:  ~/crypto-bot/venv/bin/python nvi_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def nvi_z(close, volume):
    n = len(close)
    nvi = np.ones(n)
    for i in range(1, n):
        if volume[i] < volume[i - 1]:
            nvi[i] = nvi[i - 1] * (close[i] / close[i - 1])
        else:
            nvi[i] = nvi[i - 1]
    s = pd.Series(nvi)
    z = (s - s.rolling(200).mean()) / s.rolling(200).std()
    return z.to_numpy()


def run(df, buy_th=-1.5, exit_th=0.0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    z = nvi_z(close, vol)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            if side == 1 and (z[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (z[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if z[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and z[i] > sell_th and close[i] < ma200[i]:
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
        print(f"\n=== NVI z-score buy<-1.5 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
