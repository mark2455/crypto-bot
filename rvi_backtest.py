"""
[루프 3회차-2] Relative Vigor Index (RVI) — 가격이 '얼마나 갔나'가 아니라
'그 시가~종가 움직임이 그날 변동폭 대비 얼마나 확신에 찬 방향이었나'를 측정.
(종가-시가)/(고가-저가) 를 대칭가중평균(1-2-2-1)으로 평활화, 시그널선과 교차로 신호.

RVI 신호선 크로스 (Connors RSI 골격과 동일하게 추세필터+롱숏):
  롱: RVI 가 signal 을 상향돌파 AND 가격>MA200
  숏: RVI 가 signal 을 하향돌파 AND 가격<MA200
  청산: 반대 크로스 또는 MAX_HOLD

실행:  ~/crypto-bot/venv/bin/python rvi_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def sym_weighted(x):
    """1-2-2-1 대칭가중 4봉 평활화."""
    s = pd.Series(x)
    return (s + 2 * s.shift(1) + 2 * s.shift(2) + s.shift(3)).to_numpy() / 6


def rvi(open_, high, low, close):
    a = close - open_
    b = high - low
    num = sym_weighted(a)
    den = sym_weighted(b)
    r = np.divide(num, den, out=np.zeros_like(num), where=den != 0)
    signal = sym_weighted(r)
    return r, signal


def run(df, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    open_ = df["open"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    r, signal = rvi(open_, high, low, close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            cross_down = r[i - 1] >= signal[i - 1] and r[i] < signal[i]
            cross_up = r[i - 1] <= signal[i - 1] and r[i] > signal[i]
            exit_now = (side == 1 and cross_down) or (side == -1 and cross_up) or held >= MAX_HOLD
            if exit_now:
                net = (close[i] / entry - 1 if side == 1 else 1 - close[i] / entry) - 2 * FEE
                trades.append(net); side = 0
            i += 1; continue

        cross_up = r[i - 1] <= signal[i - 1] and r[i] > signal[i]
        cross_down = r[i - 1] >= signal[i - 1] and r[i] < signal[i]
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
        print(f"\n=== RVI (신호선 크로스) — {mode_name}, 9코인 4년4국면 ===")
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
