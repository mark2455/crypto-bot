"""
[루프 5회차-2] Elder Ray (Bull Power / Bear Power) — 추세(EMA) 대비 고가/저가의 괴리로
'매수세/매도세'를 측정. 가격 그대로면 코인마다 스케일이 달라 종가 대비 %로 정규화.

BullPower% = (고가 - EMA_N) / 종가 * 100
BearPower% = (저가 - EMA_N) / 종가 * 100

신호: 롱(BearPower% 매우 낮음=과매도 + 가격>MA200) / 숏(BullPower% 매우 높음=과매수 + 가격<MA200)

실행:  ~/crypto-bot/venv/bin/python elder_ray_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 13


def elder_ray(high, low, close, n=N):
    ema = pd.Series(close).ewm(span=n, adjust=False).mean().to_numpy()
    bull = (high - ema) / close * 100
    bear = (low - ema) / close * 100
    return bull, bear


def run(df, buy_th=-3, exit_th=0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    bull, bear = elder_ray(high, low, close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    nlen = len(close)
    while i < nlen:
        if side != 0:
            held += 1
            if side == 1 and (bear[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (bull[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if bear[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and bull[i] > sell_th and close[i] < ma200[i]:
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
    bull0, bear0 = elder_ray(df0["high"].to_numpy(float), df0["low"].to_numpy(float), df0["close"].to_numpy(float))
    print(f"[분포확인] BTC BearPower%: 1%={np.percentile(bear0,1):.2f} 5%={np.percentile(bear0,5):.2f} "
          f"50%={np.percentile(bear0,50):.2f} 95%={np.percentile(bear0,95):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== Elder Ray buy<-3 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
