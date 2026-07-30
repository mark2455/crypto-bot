"""
[루프 8회차] Keltner Channel %K — 볼린저밴드와 비슷하나 표준편차 대신 ATR 사용.
(앞서 indicator_analysis.py 에서 볼린저 하단이탈은 '반등 아니라 계속하락'이었음 —
ATR 기반이면 변동성 반응이 달라 다른 결과가 나올 수 있는지 확인)

중심선 = EMA(종가, 20), ATR(10), 상단=중심+2*ATR, 하단=중심-2*ATR
%K = (종가-하단)/(상단-하단)   0=하단, 1=상단

실행:  ~/crypto-bot/venv/bin/python keltner_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def atr(high, low, close, n=10):
    prior_close = np.roll(close, 1); prior_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prior_close), np.abs(low - prior_close)))
    return pd.Series(tr).ewm(alpha=1/n, adjust=False).mean().to_numpy()


def keltner_pctk(high, low, close, n=20, mult=2):
    mid = pd.Series(close).ewm(span=n, adjust=False).mean().to_numpy()
    a = atr(high, low, close, 10)
    upper = mid + mult * a
    lower = mid - mult * a
    rng = upper - lower
    return np.divide(close - lower, rng, out=np.full_like(rng, 0.5), where=rng != 0)


def run(df, buy_th=0.1, exit_th=0.5, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    k = keltner_pctk(high, low, close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 1 - buy_th, 1 - exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            if side == 1 and (k[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (k[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if k[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and k[i] > sell_th and close[i] < ma200[i]:
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
        print(f"\n=== Keltner %K buy<0.1 exit>0.5 — {mode_name}, 9코인 4년4국면 ===")
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
