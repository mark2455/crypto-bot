"""
[루프 27회차] Commodity Channel Index (CCI, Donald Lambert 1980) — 고전 오실레이터인데
아직 검증 안 한 지표. 기각된 price_zscore_backtest.py(종가 기준, 표준편차 정규화)와 달리
CCI는 (1) 종가가 아니라 전형가격(고가+저가+종가)/3 을 쓰고, (2) 표준편차가 아니라
평균절대편차(mean absolute deviation)로 정규화한다 — 이상치에 덜 민감한 정규화 방식이라
결과가 다를 수 있음.

전형가격 TP = (고가+저가+종가)/3
CCI = (TP - SMA(TP,20)) / (0.015 * 평균절대편차(TP, SMA(TP,20), 20))

검증 결과 (2026-07-30, 롱온리 기준 — 롱숏대칭은 전 코인 전부 나쁨):
  - **BNB만 확정.** buy_th=-150~-175 × exit_th=-50~0 부근 작은 연속블록(3칸, 고립 아님)
    → 최대 buy=-175,exit=-50, 4년 +79%, 4/4
  - DOT: buy=-225 부근에서 exit=-50/+25/+50 은 4/4인데 exit=-25/0 은 3/4로 실패가 끼어있는
    체커보드 패턴(고른 연속블록 아님) → **경계선 판정, 미확정**(보수적으로 기각 취급)
  - BTC 및 나머지 코인: 격자탐색 전 구간 4/4 없음 → 기각

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/cci_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def cci(high, low, close, n=20):
    tp = (high + low + close) / 3
    tp_s = pd.Series(tp)
    sma = tp_s.rolling(n).mean()
    mad = tp_s.rolling(n).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return ((tp_s - sma) / (0.015 * mad)).to_numpy()


def run(df, buy_th=-150, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    c = cci(high, low, close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if np.isnan(c[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (c[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (c[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if c[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and c[i] > sell_th and close[i] < ma200[i]:
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
    c0 = cci(df0["high"].to_numpy(float), df0["low"].to_numpy(float), df0["close"].to_numpy(float))
    c0v = c0[~np.isnan(c0)]
    print(f"[분포확인] BTC CCI: 1%={np.percentile(c0v,1):.0f} 5%={np.percentile(c0v,5):.0f} "
          f"95%={np.percentile(c0v,95):.0f} 99%={np.percentile(c0v,99):.0f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== CCI buy<-150 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
