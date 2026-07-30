"""
[루프 24회차] Elder's Force Index (EFI, Alexander Elder — Elder Ray와 같은 저자, 다른 지표) —
"가격변화 × 거래량"을 매 봉마다 직접 곱해 그 봉의 매수/매도 압력(force)을 측정.
OBV(방향만 반영, 크기 무시)·Chaikin(고가-저가 범위 기반 MFM)·Klinger(추세부호 기반)와
전부 메커니즘이 다름 — "그 봉에서 가격이 얼마나, 얼마나 많은 거래량으로 움직였는가"를 직접 곱함.

raw_force = (종가 - 전봉종가) * 거래량
EFI = EMA(raw_force, 13)
z = (EFI - 롤링평균200) / 롤링표준편차200   (코인간 스케일 차이 보정, Chaikin/OBV/NVI와 동일 방식)

검증 결과 (2026-07-30, 롱온리 기준 — 롱숏대칭은 더 나쁨, ETC도 롱온리(+120%)가 롱숏(+83%)보다 우수):
  - DOT: exit_th=0.0 에서 buy_th −1.25~−2.00 **4칸 연속 4/4** (견고), 최대 buy=−1.25 exit=0.0 → 4년 +81%
  - ETC: exit_th=0.0 에서 buy_th −1.00~−1.50 **3칸 연속 4/4** (견고), 최대 buy=−1.00 exit=0.0 → 4년 +120%
  - LINK/SOL/BNB: 격자탐색 전 구간에서 3/4가 최선 → 미확정(참고용, 보관하지 않음)

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/force_index_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def force_index_z(close, volume, smooth=13):
    raw_force = np.diff(close, prepend=close[0]) * volume
    efi = pd.Series(raw_force).ewm(span=smooth, adjust=False).mean()
    z = (efi - efi.rolling(200).mean()) / efi.rolling(200).std()
    return z.to_numpy()


def run(df, buy_th=-1.5, exit_th=0.0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    z = force_index_z(close, vol)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 410
    n = len(close)
    while i < n:
        if np.isnan(z[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (z[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (z[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if z[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and z[i] > sell_th and close[i] < ma200[i]:
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
    z0 = force_index_z(df0["close"].to_numpy(dtype=float), df0["volume"].to_numpy(dtype=float))
    z0v = z0[~np.isnan(z0)]
    print(f"[분포확인] BTC Force Index z: 1%={np.percentile(z0v,1):.2f} 5%={np.percentile(z0v,5):.2f} "
          f"95%={np.percentile(z0v,95):.2f} 99%={np.percentile(z0v,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== Force Index z buy<-1.5 exit>0 — {mode_name}, 9코인 4년4국면 ===")
        for coin in COINS:
            df = load_candles_csv(f"data/{coin}_1h_4y.csv")
            pos = 0; yearly = []
            for start, end in PERIODS:
                mask = (df["time"] >= start) & (df["time"] < end)
                d = df[mask].reset_index(drop=True)
                if len(d) < 500:
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
