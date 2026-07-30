"""
[루프 11회차] Volume Profile POC(Point of Control) — 시장프로파일 이론.
최근 N봉의 가격구간을 몇 개 구간(bin)으로 나누고 각 구간에서 거래된 거래량을 합산,
가장 거래량이 많았던 가격대(POC, '공정가치')를 찾는다. 현재가가 POC 대비 얼마나
괴리됐는지로 평균회귀 신호 생성 (지표 계산이 아닌 '거래량 분포 구조' 기반이라 이질적).

POC는 매 REESTIMATE(24시간=1일)마다 재계산, 그사이엔 직전 값 유지.

실행:  ~/crypto-bot/venv/bin/python volprofile_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
LOOKBACK = 200
BINS = 20
REESTIMATE = 24


def poc_distance_pct(high, low, close, volume, lookback=LOOKBACK, bins=BINS, reestimate=REESTIMATE):
    n = len(close)
    poc = np.full(n, np.nan)
    typical_all = (high + low) / 2
    for i in range(lookback, n, reestimate):
        wh, wl = high[i - lookback:i], low[i - lookback:i]
        wt, wv = typical_all[i - lookback:i], volume[i - lookback:i]
        lo, hi = wl.min(), wh.max()
        if hi <= lo:
            continue
        edges = np.linspace(lo, hi, bins + 1)
        idx = np.clip(np.digitize(wt, edges) - 1, 0, bins - 1)
        vol_per_bin = np.bincount(idx, weights=wv, minlength=bins)
        b = np.argmax(vol_per_bin)
        poc_price = (edges[b] + edges[b + 1]) / 2
        end = min(i + reestimate, n)
        poc[i:end] = poc_price
    dist = (close - poc) / close * 100
    return dist


def run(df, buy_th=-3, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    dist = poc_distance_pct(high, low, close, vol)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = LOOKBACK + 10
    n = len(close)
    while i < n:
        if np.isnan(dist[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (dist[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (dist[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if dist[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and dist[i] > sell_th and close[i] < ma200[i]:
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
    d0 = poc_distance_pct(df0["high"].to_numpy(float), df0["low"].to_numpy(float),
                           df0["close"].to_numpy(float), df0["volume"].to_numpy(float))
    d0v = d0[~np.isnan(d0)]
    print(f"[분포확인] BTC POC거리%: 1%={np.percentile(d0v,1):.2f} 5%={np.percentile(d0v,5):.2f} "
          f"95%={np.percentile(d0v,95):.2f} 99%={np.percentile(d0v,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== Volume Profile POC 거리% buy<-3 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
