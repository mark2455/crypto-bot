"""
[루프 10회차-2] 가격 자체의 롤링 Z-score — 어떤 오실레이터 구성(RSI/CMO/모멘텀/거래량)도
없이, '가격이 자기 평균에서 얼마나 벗어났는지'만 직접 측정. 지금까지 성공한 지표들
(Connors RSI, CMO, TSI, Elder Ray, Chaikin, Keltner)의 성공이 각 지표의 정교한 구성 덕분인지,
아니면 그냥 '평균회귀' 자체의 힘인지 가려내는 대조군 성격의 테스트.

z = (종가 - 롤링평균N) / 롤링표준편차N

실행:  ~/crypto-bot/venv/bin/python price_zscore_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 20


def price_z(close, n=N):
    s = pd.Series(close)
    return ((s - s.rolling(n).mean()) / s.rolling(n).std()).to_numpy()


def run(df, buy_th=-2.0, exit_th=0.0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    z = price_z(close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    nlen = len(close)
    while i < nlen:
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
    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== 가격 Z-score(N={N}) buy<-2.0 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
