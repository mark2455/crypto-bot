"""
[루프 21회차] Stochastic RSI — RSI 값 자체에 다시 스토캐스틱(0~100 재정규화)을 적용해
RSI보다 훨씬 민감하게 만든 지표. Connors RSI(RSI+streak+ROC순위 합성)와 달리 RSI 하나만
반복 적용하는 단순한 변형.

RSI(14) 계산 후, 그 RSI값에 스토캐스틱 공식 적용(14기간 최고/최저 대비 위치)

실행:  ~/crypto-bot/venv/bin/python stochrsi_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv
from indicator_analysis import rsi

FEE = 0.0004
MAX_HOLD = 100


def stoch_rsi(close, rsi_n=14, stoch_n=14):
    r = rsi(close, rsi_n)
    r_s = pd.Series(r)
    lo = r_s.rolling(stoch_n).min()
    hi = r_s.rolling(stoch_n).max()
    rng = hi - lo
    return (100 * (r_s - lo) / rng).fillna(50).to_numpy()


def run(df, buy_th=10, exit_th=50, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    s = stoch_rsi(close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 100 - buy_th, 100 - exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 230
    n = len(close)
    while i < n:
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
        print(f"\n=== Stochastic RSI buy<10 exit>50 — {mode_name}, 9코인 4년4국면 ===")
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
