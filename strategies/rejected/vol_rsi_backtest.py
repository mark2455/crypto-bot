"""
[루프 20회차] Volatility RSI (Donald Dorsey) — 가격 변화가 아니라 '변동성(표준편차)의
방향'에 RSI식(Wilder 평활) 계산을 적용. 변동성 자체가 오르는지 내리는지를 오실레이터화.

std = 10봉 종가 표준편차
up_std = std (종가상승일), down_std = std (종가하락일)
RVI = 100 * WilderSmooth(up_std) / (WilderSmooth(up_std)+WilderSmooth(down_std))

실행:  ~/crypto-bot/venv/bin/python vol_rsi_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def vol_rsi(close, std_n=10, smooth_n=14):
    std = pd.Series(close).rolling(std_n).std().to_numpy()
    delta = np.diff(close, prepend=close[0])
    up_std = np.where(delta > 0, std, 0.0)
    down_std = np.where(delta < 0, std, 0.0)
    up_s = pd.Series(up_std).ewm(alpha=1 / smooth_n, adjust=False).mean().to_numpy()
    down_s = pd.Series(down_std).ewm(alpha=1 / smooth_n, adjust=False).mean().to_numpy()
    denom = up_s + down_s
    return np.divide(100 * up_s, denom, out=np.full_like(up_s, 50.0), where=denom != 0)


def run(df, buy_th=25, exit_th=50, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    v = vol_rsi(close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 100 - buy_th, 100 - exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 220
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            if side == 1 and (v[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (v[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if v[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and v[i] > sell_th and close[i] < ma200[i]:
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
        print(f"\n=== Volatility RSI buy<25 exit>50 — {mode_name}, 9코인 4년4국면 ===")
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
