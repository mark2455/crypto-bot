"""
[루프 48회차] Heikin-Ashi 괴리% — 지금까지 쓴 모든 지표는 "원본 OHLC에서 값을 계산"했는데,
이건 아예 **캔들 자체를 재귀식으로 스무딩해서 새 합성 캔들을 만든다**(平均足, 일본식 캔들
평활화 기법). 실제 종가가 이 합성(매끈한) 종가 대비 얼마나 벗어났는지를 신호로 사용 —
계산 대상 자체가 원본이 아니라 변형된 캔들이라는 점에서 근본적으로 다른 접근.

HA종가[i] = (시가+고가+저가+종가)/4
HA시가[i] = (HA시가[i-1]+HA종가[i-1])/2     (재귀식, HA시가[0]=시가[0])
%괴리 = (종가-HA종가)/종가*100   (HA종가는 매끈해서 실제 종가가 급변하면 크게 벌어짐)

실행:  ~/crypto-bot/venv/bin/python heikin_ashi_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def ha_dist_pct(open_, high, low, close):
    ha_close = (open_ + high + low + close) / 4
    m = len(close)
    ha_open = np.empty(m)
    ha_open[0] = open_[0]
    for i in range(1, m):
        ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2
    return (close - ha_close) / close * 100


def run(df, buy_th=-2.0, exit_th=0.0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    open_ = df["open"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    d = ha_dist_pct(open_, high, low, close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    m = len(close)
    while i < m:
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
        print(f"\n=== Heikin-Ashi 괴리% buy<-2.0 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
