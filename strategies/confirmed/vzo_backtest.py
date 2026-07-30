"""
[루프 38회차] Volume Zone Oscillator (VZO, Walid Khalil) — "전체 거래량 중 상승봉 거래량이
차지하는 비중"을 평활화한 지표. OBV(방향만 누적, 크기 무시)나 Force Index(가격변화폭×거래량
곱)와 달리, 거래량 자체를 부호화해서 EMA 비율로 정규화 — 자연스럽게 -100~+100 사이로 유계.

signed_vol = 거래량 (종가상승시) / -거래량 (종가하락시)
VZO = 100 * EMA(signed_vol, 14) / EMA(거래량, 14)     (-100~+100 유계)

검증 결과 (2026-07-30) — BNB만 확정, 롱숏은 전반적으로 나쁨:
  - **BNB: 롱온리.** buy=-30~-35 × exit=-5~0 4칸 전부 4/4(견고) → 최대 buy=-30,exit=0
    → 4년 +59%(4/4)
  - XRP/SOL: 3/4가 최선(4/4 없음) → 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/vzo_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def vzo(close, volume, n=14):
    delta = np.diff(close, prepend=close[0])
    signed_vol = np.where(delta > 0, volume, np.where(delta < 0, -volume, 0.0))
    ema_signed = pd.Series(signed_vol).ewm(span=n, adjust=False).mean()
    ema_vol = pd.Series(volume).ewm(span=n, adjust=False).mean()
    return (100 * ema_signed / ema_vol).to_numpy()


def run(df, buy_th=-20, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    v = vzo(close, vol)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

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
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    v0 = vzo(df0["close"].to_numpy(dtype=float), df0["volume"].to_numpy(dtype=float))
    v0v = v0[~np.isnan(v0)]
    print(f"[분포확인] BTC VZO: 1%={np.percentile(v0v,1):.1f} 5%={np.percentile(v0v,5):.1f} "
          f"95%={np.percentile(v0v,95):.1f} 99%={np.percentile(v0v,99):.1f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== VZO buy<-20 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
