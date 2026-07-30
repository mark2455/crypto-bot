"""
[루프 3회차] Aroon Indicator — 가격 크기가 아니라 '마지막 N기간 고점/저점 이후 지난 시간'을
측정하는 시간 기반 지표. RSI/CMO/Fisher/Laguerre 등 전부 가격 크기 기반이었던 것과 다른 계열.

AroonUp   = 100 * (지난 N봉 중 고점 위치) / N   (현재봉이 고점이면 100, N봉전이 고점이면 0)
AroonDown = 100 * (지난 N봉 중 저점 위치) / N
AroonOsc  = AroonUp - AroonDown   (범위 -100~100)

신호(Connors RSI/CMO와 동일 골격):
  롱: AroonOsc 가 buy_th 를 상향돌파(강한 상승추세 시작) AND 가격>MA200
      청산: AroonOsc < exit_th 또는 MAX_HOLD
  숏: AroonOsc 가 -buy_th 를 하향돌파 AND 가격<MA200
      청산: AroonOsc > -exit_th 또는 MAX_HOLD

실행:  ~/crypto-bot/venv/bin/python aroon_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 14


def aroon_osc(high, low, n=N):
    m = len(high)
    up = np.zeros(m); down = np.zeros(m)
    for i in range(n, m):
        wh = high[i - n:i + 1]
        wl = low[i - n:i + 1]
        up[i] = 100 * np.argmax(wh) / n
        down[i] = 100 * np.argmin(wl) / n
    return up - down


def run(df, buy_th=50, exit_th=0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    osc = aroon_osc(high, low, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()

    trades = []
    side = 0; entry = 0.0; held = 0
    i = max(210, n + 1)
    nlen = len(close)
    while i < nlen:
        if side != 0:
            held += 1
            if side == 1 and (osc[i] < exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (osc[i] > -exit_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        cross_up = osc[i - 1] <= buy_th and osc[i] > buy_th
        cross_down = osc[i - 1] >= -buy_th and osc[i] < -buy_th
        if cross_up and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and cross_down and close[i] < ma200[i]:
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
        print(f"\n=== Aroon Osc(N={N}) buy>50 exit<0 — {mode_name}, 9코인 4년4국면 ===")
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
