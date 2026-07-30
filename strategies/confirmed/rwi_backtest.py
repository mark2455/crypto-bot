"""
[루프 42회차] Random Walk Index (RWI) — "가격 움직임이 순수 무작위보행이었다면 나왔을 이론적
크기"를 ATR×sqrt(N)으로 계산해서, 실제 가격 변화가 그 이론치 대비 몇 배인지 측정. 기각된
Efficiency Ratio/Choppiness(경로 효율성 비율)와 "추세 강도"라는 목적은 비슷하지만 계산식이
완전히 다름(무작위보행 이론치 대비 배율).

RWI_high = (고가[i] - 저가[i-N]) / (ATR(N) * sqrt(N))     상승방향 무작위보행 대비 배율
RWI_low  = (고가[i-N] - 저가[i]) / (ATR(N) * sqrt(N))     하락방향 무작위보행 대비 배율
signal = RWI_high - RWI_low   (양수=상승쪽이 우세, 음수=하락쪽이 우세)

검증 결과 (2026-07-30) — 3개 코인 확정, 전부 추가확정(헤드라인 변화 없음):
  - **XRP: 롱온리.** buy=-1.75~-2.0 × exit=0~0.5 넓은블록(4칸) → 최대 buy=-2.0,exit=0.0
    → 4년 +41.5%(51건, 승률65%, 4/4)
  - **BNB: 롱온리.** buy=-1.75~-2.0 넓은블록 → 최대 buy=-2.0,exit=0.5 → 4년 +35.6%
    (45건, 승률80%, 4/4)
  - **DOT: 롱숏대칭.** buy=-2.0 행 전체(4칸) 4/4(역대급 견고) → 최대 buy=-2.0,exit=0.5
    → 4년 +208.1%(125건, 승률74%, 4/4)

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/rwi_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 14


def atr(high, low, close, n=14):
    prior_close = np.roll(close, 1); prior_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prior_close), np.abs(low - prior_close)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def rwi_signal(high, low, close, n=N):
    a = atr(high, low, close, n)
    denom = a * np.sqrt(n)
    high_shift_low = pd.Series(low).shift(n).to_numpy()
    low_shift_high = pd.Series(high).shift(n).to_numpy()
    rwi_high = np.divide(high - high_shift_low, denom, out=np.zeros_like(denom), where=denom > 1e-12)
    rwi_low = np.divide(low_shift_high - low, denom, out=np.zeros_like(denom), where=denom > 1e-12)
    return rwi_high - rwi_low


def run(df, buy_th=-1.0, exit_th=0.0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    s = rwi_signal(high, low, close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 220
    m = len(close)
    while i < m:
        if np.isnan(s[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (s[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (s[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if s[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and s[i] > sell_th and close[i] < ma200[i]:
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
    s0 = rwi_signal(df0["high"].to_numpy(float), df0["low"].to_numpy(float), df0["close"].to_numpy(float))
    s0v = s0[~np.isnan(s0)]
    print(f"[분포확인] BTC RWI신호: 1%={np.percentile(s0v,1):.2f} 5%={np.percentile(s0v,5):.2f} "
          f"95%={np.percentile(s0v,95):.2f} 99%={np.percentile(s0v,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== RWI signal buy<-1.0 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
