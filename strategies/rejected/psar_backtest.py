"""
[루프 10회차] Parabolic SAR — 가속계수(AF)로 추세를 따라가며 방향전환을 포착하는
스톱앤리버스 시스템. 오실레이터가 아니라 추세추종형(SuperTrend와 유사 계열이나
가속 메커니즘이 달라 별도 검증).

실행:  ~/crypto-bot/venv/bin/python psar_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 200


def parabolic_sar(high, low, af_start=0.02, af_step=0.02, af_max=0.2):
    n = len(high)
    sar = np.zeros(n); trend = np.zeros(n); ep = np.zeros(n); af = np.zeros(n)
    trend[0] = 1; sar[0] = low[0]; ep[0] = high[0]; af[0] = af_start

    for i in range(1, n):
        p_sar, p_ep, p_af, p_trend = sar[i - 1], ep[i - 1], af[i - 1], trend[i - 1]
        calc = p_sar + p_af * (p_ep - p_sar)
        lo2 = low[i - 2] if i >= 2 else low[i - 1]
        hi2 = high[i - 2] if i >= 2 else high[i - 1]

        if p_trend == 1:
            calc = min(calc, low[i - 1], lo2)
            if low[i] < calc:
                trend[i] = -1; sar[i] = p_ep; ep[i] = low[i]; af[i] = af_start
            else:
                trend[i] = 1; sar[i] = calc
                if high[i] > p_ep:
                    ep[i] = high[i]; af[i] = min(p_af + af_step, af_max)
                else:
                    ep[i] = p_ep; af[i] = p_af
        else:
            calc = max(calc, high[i - 1], hi2)
            if high[i] > calc:
                trend[i] = 1; sar[i] = p_ep; ep[i] = high[i]; af[i] = af_start
            else:
                trend[i] = -1; sar[i] = calc
                if low[i] < p_ep:
                    ep[i] = low[i]; af[i] = min(p_af + af_step, af_max)
                else:
                    ep[i] = p_ep; af[i] = p_af
    return trend


def run(df, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    trend = parabolic_sar(high, low)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            flip_down = trend[i - 1] == 1 and trend[i] == -1
            flip_up = trend[i - 1] == -1 and trend[i] == 1
            if (side == 1 and flip_down) or (side == -1 and flip_up) or held >= MAX_HOLD:
                net = (close[i] / entry - 1 if side == 1 else 1 - close[i] / entry) - 2 * FEE
                trades.append(net); side = 0
            i += 1; continue

        flip_up = trend[i - 1] == -1 and trend[i] == 1
        flip_down = trend[i - 1] == 1 and trend[i] == -1
        if flip_up and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and flip_down and close[i] < ma200[i]:
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
        print(f"\n=== Parabolic SAR 방향전환 — {mode_name}, 9코인 4년4국면 ===")
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
