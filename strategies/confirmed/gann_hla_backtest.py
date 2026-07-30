"""
[루프 41회차] Gann High-Low Activator (W.D. Gann) — 상승상태면 저가의 이동평균을 지지선으로,
하락상태면 고가의 이동평균을 저항선으로 삼는 2진 상태기계. 종가가 활성선을 넘으면 상태가
전환된다. (순수 스탑앤리버스로 쓰면 SuperTrend/PSAR처럼 실패할 가능성이 높다는 기존 설계원칙에
따라, 이 활성선 대비 괴리%를 극단값+되돌림+MA200 프레임에 적용해서 검증 — 상태전환 자체를
매매신호로 안 쓰고 "활성선에서 얼마나 괴리됐나"만 신호로 사용.)

active_line = SMA(저가,N)  (상승상태) / SMA(고가,N)  (하락상태)
상태전환: 종가가 활성선을 반대로 넘으면 전환 (N=10)
%괴리 = (종가-active_line)/종가*100

검증 결과 (2026-07-30) — BNB만 확정:
  - **BNB: 롱온리.** buy=-2.5~-3.0 전체 행(8칸) + buy=-4.0 일부 견고블록 → 최대 buy=-2.5,exit=0.0
    → 4년 +84%(4/4)
  - XRP/ETC/BTC: 3/4가 최선(4/4 없음) → 미확정
  - SOL: buy=-2.0,exit=1.0 단일 고립셀만 4/4 → 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/gann_hla_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 10


def gann_hla_dist_pct(high, low, close, n=N):
    sma_high = pd.Series(high).rolling(n).mean().to_numpy()
    sma_low = pd.Series(low).rolling(n).mean().to_numpy()
    m = len(close)
    active = np.full(m, np.nan)
    state = 1  # 1=상승(저가SMA 사용), -1=하락(고가SMA 사용)
    for i in range(n, m):
        line = sma_low[i] if state == 1 else sma_high[i]
        if state == 1 and close[i] < line:
            state = -1
            line = sma_high[i]
        elif state == -1 and close[i] > line:
            state = 1
            line = sma_low[i]
        active[i] = line
    return (close - active) / close * 100


def run(df, buy_th=-2.0, exit_th=0.0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    d = gann_hla_dist_pct(high, low, close, n)
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
        print(f"\n=== Gann HLA 괴리% buy<-2.0 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
