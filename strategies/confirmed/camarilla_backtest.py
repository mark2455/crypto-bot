"""
[루프 50회차] Camarilla Pivot — Pivot Point((H+L+C)/3를 기준점으로 삼음)와 달리, **전일
종가 자체**를 기준점으로 삼고 전일 변동폭(고가-저가)의 배수만큼 떨어진 곳을 지지/저항으로
본다. 기준점 계산 방식이 다르고, "오늘 종가가 어제 종가 대비 어제 변동폭의 몇 배나 움직였나"
라는 전혀 다른 정규화.

전일 range = 전일고가-전일저가
%괴리 = (종가-전일종가) / 전일range * 100   (전일 변동폭 대비 오늘 누적 이동폭)

검증 결과 (2026-07-30) — 4개 코인 확정, 전부 추가확정(헤드라인 변화 없음):
  - **DOT: 롱온리.** buy=-50~-70,exit=-20 3칸 연속 + buy=-40~-60,exit=0 3칸 연속 → 최대
    buy=-50,exit=-20 → 4년 +87.6%(129건, 승률57%, 4/4)
  - **LINK: 롱온리.** buy=-30~-50,exit=0 3칸 연속 → buy=-40,exit=0 → +77.0%(191건, 승률55%, 4/4)
  - **BTC: 롱온리.** buy=-40~-50,exit=40 2칸 연속 → buy=-40,exit=40 → +81.8%(167건, 승률69%, 4/4)
  - **BNB: 롱온리.** buy=-70 행 exit=0~40 3칸 연속 → buy=-70,exit=40 → +101.1%(62건, 승률73%, 4/4)

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/camarilla_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def camarilla_dist_pct(df):
    d = df.copy()
    d["date"] = d["time"].dt.date
    daily = d.groupby("date").agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
    daily["range"] = daily["high"] - daily["low"]
    prev_close = daily["close"].shift(1)
    prev_range = daily["range"].shift(1)
    pc_map = prev_close.to_dict()
    pr_map = prev_range.to_dict()
    pc_series = d["date"].map(pc_map).to_numpy(dtype=float)
    pr_series = d["date"].map(pr_map).to_numpy(dtype=float)
    close = d["close"].to_numpy(dtype=float)
    dist = np.divide(close - pc_series, pr_series, out=np.full(len(close), np.nan), where=pr_series > 1e-9) * 100
    return dist


def run(df, buy_th=-50, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    d = camarilla_dist_pct(df)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
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
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    d0 = camarilla_dist_pct(df0)
    d0v = d0[~np.isnan(d0)]
    print(f"[분포확인] BTC Camarilla 괴리%: 1%={np.percentile(d0v,1):.1f} 5%={np.percentile(d0v,5):.1f} "
          f"50%={np.percentile(d0v,50):.1f} 95%={np.percentile(d0v,95):.1f} 99%={np.percentile(d0v,99):.1f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== Camarilla 괴리% buy<-50 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
