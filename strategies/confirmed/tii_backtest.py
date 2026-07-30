"""
[루프 49회차] Trend Intensity Index (TII) — 일반 RSI는 "가격변화(오늘종가-어제종가)"에
상승/하락일 여부를 매기는데, 이건 "이동평균 대비 가격이 위/아래 어느 쪽에 있었나"를 RSI식으로
평활한다. 즉 매 시점 가격 자체의 등락이 아니라 '평균선 위/아래 위치'의 지속성을 측정 — CCI나
Bollinger(괴리 크기 직접 측정)와도 다르고, 일반 RSI(가격변화 크기)와도 다름.

deviation = 종가 - SMA(종가, N)
up = deviation (deviation>0 인 시점만), down = -deviation (deviation<0 인 시점만)
TII = 100 * SMA(up, N) / (SMA(up,N) + SMA(down,N))     0~100 유계, RSI처럼 50 중심

검증 결과 (2026-07-30) — 분포가 0/100에 심하게 몰림(5%=0, 95%=100), LINK만 확정:
  - **LINK: 롱온리.** exit=40 열이 buy 20~30 3칸 연속 4/4 → 최대 buy=30,exit=40
    → 4년 +170.7%(264건, 승률65%, 4/4). 헤드라인(FRAMA +301.1%)엔 못 미쳐 추가확정
  - ETC: 3/4가 최선(4/4 없음) → 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/tii_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 20


def tii(close, n=N):
    c = pd.Series(close, dtype=float)
    sma = c.rolling(n).mean()
    dev = c - sma
    up = dev.where(dev > 0, 0.0)
    down = (-dev).where(dev < 0, 0.0)
    up_avg = up.rolling(n).mean()
    down_avg = down.rolling(n).mean()
    denom = up_avg + down_avg
    return (100 * up_avg / denom).to_numpy()


def run(df, buy_th=20, exit_th=50, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    t = tii(close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 100 - buy_th, 100 - exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 2 * n + 10
    m = len(close)
    while i < m:
        if np.isnan(t[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (t[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (t[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if t[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and t[i] > sell_th and close[i] < ma200[i]:
            side, entry, held = -1, close[i], 0
        i += 1

    if not trades:
        return {"trades": 0, "return": 0.0, "win_rate": 0.0}
    tt = np.array(trades)
    return {"trades": len(tt), "return": (np.prod(1 + tt) - 1) * 100, "win_rate": (tt > 0).mean() * 100}


COINS = ["DOTUSDT", "LTCUSDT", "LINKUSDT", "XRPUSDT", "ETCUSDT",
         "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
PERIODS = [("2022-07-30", "2023-07-30"), ("2023-07-30", "2024-07-30"),
           ("2024-07-30", "2025-07-30"), ("2025-07-30", "2026-07-29")]


def main():
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    t0 = tii(df0["close"].to_numpy(dtype=float))
    t0v = t0[~np.isnan(t0)]
    print(f"[분포확인] BTC TII: 1%={np.percentile(t0v,1):.1f} 5%={np.percentile(t0v,5):.1f} "
          f"50%={np.percentile(t0v,50):.1f} 95%={np.percentile(t0v,95):.1f} 99%={np.percentile(t0v,99):.1f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== TII buy<20 exit>50 — {mode_name}, 9코인 4년4국면 ===")
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
