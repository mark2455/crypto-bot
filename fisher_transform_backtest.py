"""
Ehlers Fisher Transform — 신호처리 이론 기반의 덜 알려진 지표.
RSI/MACD 계열과 수학적 원리가 다름(가격 분포를 정규화 후 Fisher 변환으로 전환점을 강조).

공식(Ehlers 원안, N=10):
  raw = (high+low)/2
  x   = 0.33 * 2*(raw - min(low,N))/(max(high,N)-min(low,N)) - 1 + 0.67*x[전봉]   (정규화, -1~1로 clamp)
  fisher = 0.5*ln((1+x)/(1-x)) + 0.5*fisher[전봉]
  signal = fisher[전봉]  (자기 자신의 1봉 지연선)

신호(추세필터 포함, Connors RSI와 동일한 골격):
  롱: fisher 가 signal 을 상향돌파 AND 가격>MA200(상승추세)
  숏: fisher 가 signal 을 하향돌파 AND 가격<MA200(하락추세)
  청산: 반대 방향 돌파 또는 MAX_HOLD

실행:  ~/crypto-bot/venv/bin/python fisher_transform_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

N = 10
FEE = 0.0004
MAX_HOLD = 100
EXTREME = 1.5   # 이 값을 넘어선 상태에서 돌아설 때만 신호 인정 (잦은 휩쏘 방지)


def fisher_transform(high, low, n=N):
    raw = (high + low) / 2
    length = len(raw)
    x = np.zeros(length)
    fisher = np.zeros(length)
    for i in range(n, length):
        hi = raw[i - n + 1:i + 1].max()
        lo = raw[i - n + 1:i + 1].min()
        if hi == lo:
            x[i] = x[i - 1]
        else:
            v = 0.33 * 2 * ((raw[i] - lo) / (hi - lo) - 0.5) + 0.67 * x[i - 1]
            x[i] = min(max(v, -0.999), 0.999)
        fisher[i] = 0.5 * np.log((1 + x[i]) / (1 - x[i])) + 0.5 * fisher[i - 1]
    return fisher


def run(df, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    fish = fisher_transform(high, low)
    signal = np.roll(fish, 1)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            cross_down = fish[i - 1] >= signal[i - 1] and fish[i] < signal[i]
            cross_up = fish[i - 1] <= signal[i - 1] and fish[i] > signal[i]
            exit_now = (side == 1 and cross_down) or (side == -1 and cross_up) or held >= MAX_HOLD
            if exit_now:
                net = (close[i] / entry - 1 if side == 1 else 1 - close[i] / entry) - 2 * FEE
                trades.append(net); side = 0
            i += 1; continue

        cross_up = fish[i - 1] <= signal[i - 1] and fish[i] > signal[i] and fish[i - 1] < -EXTREME
        cross_down = fish[i - 1] >= signal[i - 1] and fish[i] < signal[i] and fish[i - 1] > EXTREME
        if cross_up and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and cross_down and close[i] < ma200[i]:
            side, entry, held = -1, close[i], 0
        i += 1

    if not trades:
        return {"trades": 0, "return": 0.0, "win_rate": 0.0}
    t = np.array(trades)
    return {"trades": len(t), "return": (np.prod(1 + t) - 1) * 100, "win_rate": (t > 0).mean() * 100}


def main():
    COINS = ["DOTUSDT", "LTCUSDT", "LINKUSDT", "XRPUSDT", "ETCUSDT",
             "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
    periods = [
        ("2022-07-30", "2023-07-30"), ("2023-07-30", "2024-07-30"),
        ("2024-07-30", "2025-07-30"), ("2025-07-30", "2026-07-29"),
    ]
    print(f"=== Ehlers Fisher Transform (N={N}) 롱숏+추세필터 — 9개 코인 4년 ===\n")
    for coin in COINS:
        df = load_candles_csv(f"data/{coin}_1h_4y.csv")
        pos = 0
        yearly = []
        for start, end in periods:
            mask = (df["time"] >= start) & (df["time"] < end)
            d = df[mask].reset_index(drop=True)
            if len(d) < 300:
                continue
            r = run(d)
            yearly.append(r["return"])
            if r["return"] > 0:
                pos += 1
        r_full = run(df)
        mark = "★" if pos == 4 else ""
        yearly_str = "  ".join(f"{y:+7.1f}%" for y in yearly)
        print(f"{coin.replace('USDT',''):6} {yearly_str}   4년합계 {r_full['return']:+8.2f}%  {pos}/4 {mark}")


if __name__ == "__main__":
    main()
