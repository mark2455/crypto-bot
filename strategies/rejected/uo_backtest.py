"""
[루프 4회차-2] Ultimate Oscillator — 3개 시간대(7/14/28기간) 매수압력을 가중합쳐
단일 오실레이터(0~100)로 만든 지표. Connors RSI/CMO와 같은 극단값+되돌림 방식.

BP(매수압력) = 종가 - min(저가, 전일종가)
TR(진범위)   = max(고가, 전일종가) - min(저가, 전일종가)
Avg7/14/28  = Σ7/14/28(BP) / Σ7/14/28(TR)
UO = 100 * (4*Avg7 + 2*Avg14 + 1*Avg28) / 7

실행:  ~/crypto-bot/venv/bin/python uo_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def ultimate_osc(high, low, close):
    prior_close = np.roll(close, 1); prior_close[0] = close[0]
    bp = close - np.minimum(low, prior_close)
    tr = np.maximum(high, prior_close) - np.minimum(low, prior_close)
    bp_s, tr_s = pd.Series(bp), pd.Series(tr)
    avg7 = (bp_s.rolling(7).sum() / tr_s.rolling(7).sum())
    avg14 = (bp_s.rolling(14).sum() / tr_s.rolling(14).sum())
    avg28 = (bp_s.rolling(28).sum() / tr_s.rolling(28).sum())
    uo = 100 * (4 * avg7 + 2 * avg14 + avg28) / 7
    return uo.to_numpy()


def run(df, buy_th=20, exit_th=50, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    uo = ultimate_osc(high, low, close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 100 - buy_th, 100 - exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            if side == 1 and (uo[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (uo[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if uo[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and uo[i] > sell_th and close[i] < ma200[i]:
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
        print(f"\n=== Ultimate Oscillator buy<20 exit>50 — {mode_name}, 9코인 4년4국면 ===")
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
