"""
[루프 15회차] Coppock Curve — 서로 다른 두 기간의 ROC(변화율)를 더해 가중이동평균으로
평활화. 원래 장기(월봉) 주요 저점 포착용으로 설계된 지표. 우리 시간봉에 맞게 기간 조정.

Coppock = WMA(ROC(종가,14) + ROC(종가,11), 10)
%Coppock = Coppock / 종가 * 100 (정규화)

실행:  ~/crypto-bot/venv/bin/python coppock_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv
from hma_backtest import wma

FEE = 0.0004
MAX_HOLD = 100


def coppock_pct(close, r1=14, r2=11, wma_n=10):
    roc1 = pd.Series(close).pct_change(r1) * 100
    roc2 = pd.Series(close).pct_change(r2) * 100
    combined = (roc1 + roc2).to_numpy()
    cop = wma(combined, wma_n)
    return cop  # 이미 %단위(ROC가 %라서)


def run(df, buy_th=-10, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    c = coppock_pct(close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
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
    c0 = coppock_pct(df0["close"].to_numpy(dtype=float))
    c0v = c0[~np.isnan(c0)]
    print(f"[분포확인] BTC Coppock: 1%={np.percentile(c0v,1):.1f} 5%={np.percentile(c0v,5):.1f} "
          f"95%={np.percentile(c0v,95):.1f} 99%={np.percentile(c0v,99):.1f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== Coppock Curve buy<-10 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
