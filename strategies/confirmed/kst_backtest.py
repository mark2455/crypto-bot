"""
[루프 31회차] Know Sure Thing (KST, Martin Pring) — Coppock(ROC 2개 비가중합)이나
TRIX(ROC 1개를 3중평활)와 달리, 서로 다른 4개 기간(10/15/20/30봉)의 ROC를 각각 평활한 뒤
1:2:3:4 가중치로 합산하는 모멘텀 지표. "여러 시간축의 모멘텀을 한번에 합의"시키는 방식이라
단일 ROC 기반 지표들과 구조가 다름.

ROC1=ROC(10)→SMA10,  ROC2=ROC(15)→SMA10,  ROC3=ROC(20)→SMA10,  ROC4=ROC(30)→SMA15
KST = 1*ROC1s + 2*ROC2s + 3*ROC3s + 4*ROC4s   (이미 %단위)

검증 결과 (2026-07-30) — 이번 루프 최대 수확, 4개 코인 확정:
  - **DOT: 롱숏대칭.** buy=-25~-30 × exit=-10~10 넓은 2D블록(6칸+ 전부 4/4) — 최대
    buy=-25,exit=0 → 4년 +138.3%(148건, 승률66%, 4/4). 롱온리는 +62%로 더 낮음
  - **BTC: 롱숏대칭.** buy=-30~-35 × exit 전반 넓은 블록(buy=-35 행 전체 4칸 4/4) — 최대
    buy=-35,exit=10 → 4년 +32.5%(18건, 승률83%, 4/4). **BTC 역대 최다 거래수** — 기존 확정
    지표들(Coppock 4건, NVI 등)보다 훨씬 통계적으로 신뢰 가능
  - **LTC: 롱온리.** buy=-25~-30 × exit∈{-10,10,20} 블록(중앙 exit=0만 3/4로 빠짐) — 최대
    buy=-30,exit=-10 → 4년 +46.1%(43건, 승률63%, 4/4)
  - **SOL: 롱온리.** buy=-35 행 대부분(exit -10,0,20) 4/4 — 최대 buy=-35,exit=20
    → 4년 +106.7%(47건, 승률77%, 4/4)

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/kst_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def kst(close):
    c = pd.Series(close)
    r1 = (c.pct_change(10) * 100).rolling(10).mean()
    r2 = (c.pct_change(15) * 100).rolling(10).mean()
    r3 = (c.pct_change(20) * 100).rolling(10).mean()
    r4 = (c.pct_change(30) * 100).rolling(15).mean()
    return (1 * r1 + 2 * r2 + 3 * r3 + 4 * r4).to_numpy()


def run(df, buy_th=-30, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    k = kst(close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 220
    n = len(close)
    while i < n:
        if np.isnan(k[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (k[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (k[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if k[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and k[i] > sell_th and close[i] < ma200[i]:
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
    k0 = kst(df0["close"].to_numpy(dtype=float))
    k0v = k0[~np.isnan(k0)]
    print(f"[분포확인] BTC KST: 1%={np.percentile(k0v,1):.1f} 5%={np.percentile(k0v,5):.1f} "
          f"95%={np.percentile(k0v,95):.1f} 99%={np.percentile(k0v,99):.1f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== KST buy<-30 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
