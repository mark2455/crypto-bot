"""
[루프 28회차] Donchian Channel %Position (Richard Donchian) — Keltner(EMA중심+ATR밴드,
평활화됨)와 달리 아무 평활화 없이 최근 N봉의 순수 최고가/최저가 그 자체로 채널을 만든다.
"최근 N봉 범위 안에서 지금 가격이 어디에 있는가"만 보는 가장 원초적인 채널 지표.

상단 = 최근 N봉 최고가, 하단 = 최근 N봉 최저가
%Position = (종가-하단)/(상단-하단)   0=최저가 터치, 1=최고가 터치

검증 결과 (2026-07-30, 롱온리 기준 — 3개 코인 확정, 전부 롱숏보다 롱온리가 우수):
  - **BNB: buy=0.02~0.05 × exit=0.3~0.6 넓은 2D블록(7칸 이상 전부 4/4)** — 역대급 견고.
    최대 buy=0.05,exit=0.5 → 4년 +80.3%(135건, 4/4)
  - **XRP: buy=0.02 행이 exit 0.3~0.7 전부(5칸) 4/4** — 최대 buy=0.02,exit=0.4 → +58.9%(29건, 4/4)
  - **LINK: exit=0.7 열이 buy 0.02~0.10 전부(3칸) 4/4** — 최대 buy=0.02,exit=0.7 → +96.8%(57건, 4/4)
  - ETC: buy=0.02,exit=0.7 단일 고립셀만 4/4 → 미확정(우연 판정)
  - BTC 및 나머지: 4/4 없음 → 기각

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/donchian_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 20


def donchian_pct(high, low, close, n=N):
    upper = pd.Series(high).rolling(n).max().to_numpy()
    lower = pd.Series(low).rolling(n).min().to_numpy()
    rng = upper - lower
    return np.divide(close - lower, rng, out=np.full_like(rng, 0.5), where=rng != 0)


def run(df, buy_th=0.1, exit_th=0.5, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    p = donchian_pct(high, low, close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 1 - buy_th, 1 - exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    m = len(close)
    while i < m:
        if side != 0:
            held += 1
            if side == 1 and (p[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (p[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if p[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and p[i] > sell_th and close[i] < ma200[i]:
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
        print(f"\n=== Donchian %Pos buy<0.1 exit>0.5 — {mode_name}, 9코인 4년4국면 ===")
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
