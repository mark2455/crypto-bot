"""
[루프 30회차] Chaikin Volatility (Marc Chaikin — Chaikin Oscillator와 같은 저자, 완전히
다른 지표) — 자금흐름(ADL)이 아니라 "변동성 자체가 얼마나 빠르게 커지거나 줄고 있는가"를
측정. 지금까지 검증한 모든 지표는 방향성(모멘텀/자금흐름/거래량)을 봤는데, 이건 유일하게
"변동성의 변화율"만 본다 — 극단적 수축(코일링) 후 방향 베팅이라는 다른 논리.

spread = 고가-저가
ema_spread = EMA(spread, 10)
ChaikinVol = (ema_spread - ema_spread(10봉전)) / ema_spread(10봉전) * 100

극단적으로 낮은(음수, 변동성 급격히 수축) + MA200 위 = 코일링 후 상승 기대
극단적으로 높은(양수, 변동성 급격히 팽창) + MA200 아래 = 급락 후 반등 기대(숏 청산 관점 아님, 대칭 적용만)

실행:  ~/crypto-bot/venv/bin/python chaikin_vol_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def chaikin_vol(high, low, ema_n=10, roc_n=10):
    spread = high - low
    ema_spread = pd.Series(spread).ewm(span=ema_n, adjust=False).mean()
    cv = (ema_spread - ema_spread.shift(roc_n)) / ema_spread.shift(roc_n) * 100
    return cv.to_numpy()


def run(df, buy_th=-40, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    cv = chaikin_vol(high, low)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 220
    n = len(close)
    while i < n:
        if np.isnan(cv[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (cv[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (cv[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if cv[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and cv[i] > sell_th and close[i] < ma200[i]:
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
    cv0 = chaikin_vol(df0["high"].to_numpy(float), df0["low"].to_numpy(float))
    cv0v = cv0[~np.isnan(cv0)]
    print(f"[분포확인] BTC ChaikinVol: 1%={np.percentile(cv0v,1):.0f} 5%={np.percentile(cv0v,5):.0f} "
          f"95%={np.percentile(cv0v,95):.0f} 99%={np.percentile(cv0v,99):.0f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== ChaikinVol buy<-40 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
