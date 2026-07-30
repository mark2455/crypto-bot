"""
[루프 36회차] Mass Index (Donald Dorsey) — 봉 하나하나의 범위(고가-저가)를 이중 지수평활한
뒤 그 비율을 25봉 합산 — "범위가 최근 급격히 확장/수축했는가"를 측정. 기각된 Chaikin
Volatility(EMA된 범위의 변화율)와는 다른 계산 메커니즘(단일/이중 EMA의 비율을 합산하는 방식).

spread = 고가-저가
single_ema = EMA(spread, 9),  double_ema = EMA(single_ema, 9)
ratio = single_ema / double_ema
MassIndex = rolling_sum(ratio, 25)     (보통 25 근방에서 진동, 27 넘으면 '범위 팽창')
z = (MI - 롤링평균200) / 롤링표준편차200

검증 결과 (2026-07-30):
  - **SOL: 롱숏대칭.** buy=-1.50 에서 exit=-0.5/0.0 두 칸 연속 4/4(얇지만 인접, 고립셀 아님)
    → 최대 buy=-1.5,exit=-0.5 → 4년 +68%(4/4). 기존 헤드라인(Ulcer Index +306.1%)엔 못 미쳐
    추가 확정으로만 기록
  - ETH: buy=-1.5,exit=0.0 단일 고립셀만 4/4(사방 전부 1~3/4) → **미확정**(우연 판정)
  - LINK: 3/4가 최선 → 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/mass_index_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def mass_index_z(high, low, ema_n=9, sum_n=25):
    spread = high - low
    single = pd.Series(spread).ewm(span=ema_n, adjust=False).mean()
    double = single.ewm(span=ema_n, adjust=False).mean()
    ratio = single / double
    mi = ratio.rolling(sum_n).sum()
    z = (mi - mi.rolling(200).mean()) / mi.rolling(200).std()
    return z.to_numpy()


def run(df, buy_th=-1.5, exit_th=0.0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    z = mass_index_z(high, low)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 240
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
    z0 = mass_index_z(df0["high"].to_numpy(float), df0["low"].to_numpy(float))
    z0v = z0[~np.isnan(z0)]
    print(f"[분포확인] BTC MassIndex z: 1%={np.percentile(z0v,1):.2f} 5%={np.percentile(z0v,5):.2f} "
          f"95%={np.percentile(z0v,95):.2f} 99%={np.percentile(z0v,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== MassIndex z buy<-1.5 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
