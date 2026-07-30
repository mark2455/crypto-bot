"""
[루프 46회차] Weighted Close 괴리% — CCI가 쓰는 전형가격(고가+저가+종가)/3보다 종가에
가중치를 더 준 버전. 고가·저가는 그대로 반영하되 종가를 2배로 반영해 "일봉 마감 심리"를
더 강조 — 전형가격 대비 종가 쏠림이 있는 코인에서 다르게 작동할 수 있음.

WC = (고가+저가+2*종가)/4
WC_MA = SMA(WC, 20)
%괴리 = (WC-WC_MA)/WC*100

검증 결과 (2026-07-30) — **3개 코인 확정, BNB 헤드라인 교체**:
  - **BNB: 롱온리.** buy=-1.5,exit=0.0 (buy-2.0~-4.0 넓은블록+buy-1.5 단일 지점) → 4년
    **+132.9%**(146건, 승률74%, 4/4). **헤드라인 교체**(구: HMA +90.5%)
  - **LINK: 롱온리.** buy=-2.5~-3.0 전체 행(8칸) 역대급 견고 → 최대 buy=-2.5,exit=0.5
    → +196.2%(123건, 승률69%, 4/4). 헤드라인(FRAMA +301.1%)엔 못 미쳐 추가확정
  - **XRP: 롱온리.** buy=-2.0 행 대부분(3칸) → 최대 buy=-2.0,exit=-0.5 → +164.2%(145건,
    승률67%, 4/4). 헤드라인(McGinley +196.0%)엔 못 미쳐 추가확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/weighted_close_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 20


def wc_dist_pct(high, low, close, n=N):
    wc = (high + low + 2 * close) / 4
    wc_ma = pd.Series(wc).rolling(n).mean().to_numpy()
    return (wc - wc_ma) / wc * 100


def run(df, buy_th=-2.0, exit_th=0.0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    d = wc_dist_pct(high, low, close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    m = len(close)
    while i < m:
        if np.isnan(d[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (d[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (d[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if d[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and d[i] > sell_th and close[i] < ma200[i]:
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
        print(f"\n=== Weighted Close 괴리% buy<-2.0 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
