"""
[루프 57회차] Volume-Weighted TRIX (VWMA 기반) — 확정된 TRIX(3중 EMA 평활 후 변화율)에서
EMA를 **VWMA(거래량가중이동평균)**로 바꾼 버전. VW-PPO에서 통했던 "EMA→VWMA 교체" 패턴을
3단계 평활에 적용 — TRIX는 이미 ETC에서 확정됐지만 거래량가중판은 다른 코인에서 반응하는지 확인.

VWMA(n) = sum(종가*거래량,n)/sum(거래량,n)
e1=VWMA(종가,N), e2=VWMA(e1,N), e3=VWMA(e2,N)   (e2/e3 단계는 거래량을 다시 씌우지 않고
그대로 값 자체를 N봉 단순평균해 재적용 — 원 TRIX의 "EMA의 EMA의 EMA" 구조를 모사)
VW-TRIX = (e3[i]-e3[i-1])/e3[i-1]*100

실행:  ~/crypto-bot/venv/bin/python vw_trix_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 14


def vwma_series(values, volume, n):
    pv = pd.Series(values * volume).rolling(n).sum()
    v = pd.Series(volume).rolling(n).sum()
    return (pv / v).to_numpy()


def vw_trix(close, volume, n=N):
    e1 = vwma_series(close, volume, n)
    e2 = vwma_series(e1, volume, n)
    e3 = vwma_series(e2, volume, n)
    e3_s = pd.Series(e3)
    return (e3_s.pct_change() * 100).to_numpy()


def run(df, buy_th=-0.3, exit_th=0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    t = vw_trix(close, vol, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 3 * n + 10
    m = len(close)
    while i < m:
        if np.isnan(t[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (t[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (t[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if t[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and t[i] > sell_th and close[i] < ma200[i]:
            side, entry, held = -1, close[i], 0
        i += 1

    if not trades:
        return {"trades": 0, "return": 0.0, "win_rate": 0.0}
    tt = np.array(trades)
    return {"trades": len(tt), "return": (np.prod(1 + tt) - 1) * 100, "win_rate": (tt > 0).mean() * 100}


COINS = ["DOTUSDT", "LTCUSDT", "LINKUSDT", "XRPUSDT", "ETCUSDT",
         "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
PERIODS = [("2022-07-30", "2023-07-30"), ("2023-07-30", "2024-07-30"),
           ("2024-07-30", "2025-07-30"), ("2025-07-30", "2026-07-29")]


def main():
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    t0 = vw_trix(df0["close"].to_numpy(dtype=float), df0["volume"].to_numpy(dtype=float))
    t0v = t0[~np.isnan(t0)]
    print(f"[분포확인] BTC VW-TRIX: 1%={np.percentile(t0v,1):.3f} 5%={np.percentile(t0v,5):.3f} "
          f"50%={np.percentile(t0v,50):.3f} 95%={np.percentile(t0v,95):.3f} 99%={np.percentile(t0v,99):.3f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== VW-TRIX buy<-0.3 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
