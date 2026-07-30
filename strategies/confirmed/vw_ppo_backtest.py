"""
[루프 56회차] Volume-Weighted PPO (VWMA 기반) — 확정된 PPO(EMA12-EMA26의 %차이)에서
EMA를 **VWMA(거래량가중이동평균)**로 바꾼 버전. VW-RSI/VW-TSI처럼 "gain/loss에 거래량 곱하기"
방식이 아니라, 평균 계산 자체를 거래량가중으로 바꾸는 다른 접근 — 거래량이 몰린 시점의 가격이
평균에 더 크게 반영됨.

VWMA(n) = sum(종가*거래량, n) / sum(거래량, n)
VW-PPO = (VWMA(12) - VWMA(26)) / VWMA(26) * 100

검증 결과 (2026-07-30) — 3개 코인 확정, 전부 추가확정(헤드라인 변화 없음), ETH는 역대급 견고블록:
  - **DOT: 롱숏대칭.** buy=-2.0,exit=0.0 (buy=-2.0 행 대부분) → 4년 +163.0%(103건, 승률65%, 4/4).
    헤드라인(VW-RSI +438.2%)엔 못 미쳐 추가확정
  - **ETH: 롱숏대칭.** buy=-2.0~-3.0 **3개 행 전부(12칸) 4/4**(역대급 견고) → 최대 buy=-2.0,exit=1.0
    → +138.7%(50건, 승률72%, 4/4). 헤드라인(Coppock +166.7%)엔 못 미쳐 추가확정
  - **BTC: 롱숏대칭.** buy=-1.5~-2.5 넓은블록 → 최대 buy=-2.0,exit=1.0 → +37.1%(18건, 승률89%, 4/4).
    헤드라인(VHF +225.7%)엔 못 미쳐 추가확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/vw_ppo_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def vwma(close, volume, n):
    pv = pd.Series(close * volume).rolling(n).sum()
    v = pd.Series(volume).rolling(n).sum()
    return (pv / v).to_numpy()


def vw_ppo(close, volume, fast=12, slow=26):
    vw_fast = vwma(close, volume, fast)
    vw_slow = vwma(close, volume, slow)
    return (vw_fast - vw_slow) / vw_slow * 100


def run(df, buy_th=-2, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    p = vw_ppo(close, vol)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 220
    m = len(close)
    while i < m:
        if np.isnan(p[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (p[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (p[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if p[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and p[i] > sell_th and close[i] < ma200[i]:
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
    p0 = vw_ppo(df0["close"].to_numpy(dtype=float), df0["volume"].to_numpy(dtype=float))
    p0v = p0[~np.isnan(p0)]
    print(f"[분포확인] BTC VW-PPO: 1%={np.percentile(p0v,1):.2f} 5%={np.percentile(p0v,5):.2f} "
          f"50%={np.percentile(p0v,50):.2f} 95%={np.percentile(p0v,95):.2f} 99%={np.percentile(p0v,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== VW-PPO buy<-2 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
