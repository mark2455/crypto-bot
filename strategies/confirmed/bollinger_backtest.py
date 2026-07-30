"""
[루프 43회차] Bollinger Bands %B — Keltner Channel(EMA중심+ATR밴드, 이미 확정 최우수급)과
개념은 같은 "채널 내 위치"지만 변동성 측정 방식이 다르다: Keltner는 ATR(방향성 포함 진폭),
Bollinger는 표준편차(단순 분산)를 쓴다. 초기 탐색(indicator_analysis.py, MA200 필터 없음)에서는
"볼린저 하단이탈=하락지속"이라는 경고가 있었지만, MA200 추세필터를 붙인 지금 프레임에서는
Keltner처럼 다르게 작동하는지 정식 검증한 적이 없어 확인.

중심선 = SMA(종가,20), 표준편차(종가,20), 상단=중심+2*표준편차, 하단=중심-2*표준편차
%B = (종가-하단)/(상단-하단)   0=하단터치, 1=상단터치

검증 결과 (2026-07-30) — MA200 필터 붙이니 초기 경고("하단이탈=하락지속")와 달리 정상 작동,
2개 코인 확정(둘 다 추가확정, 헤드라인 변화 없음):
  - **BNB: 롱온리.** buy=0.02~0.10 × exit=0.4~0.5 견고블록(6칸) → 최대 buy=0.02,exit=0.4
    → 4년 +83.5%(274건, 승률70%, 4/4)
  - **LINK: 롱온리.** buy=0.10 에서 exit=0.6/0.7 두 칸 연속(얇지만 인접) → buy=0.10,exit=0.6
    → 4년 +98.7%(297건, 승률64%, 4/4)
  - DOT/XRP: 3/4가 최선(4/4 없음) → 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/bollinger_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def bollinger_pctb(close, n=20, mult=2):
    c = pd.Series(close)
    mid = c.rolling(n).mean()
    std = c.rolling(n).std()
    upper = mid + mult * std
    lower = mid - mult * std
    rng = upper - lower
    return np.divide((close - lower.to_numpy()), rng.to_numpy(),
                      out=np.full_like(rng.to_numpy(), 0.5), where=rng.to_numpy() != 0)


def run(df, buy_th=0.1, exit_th=0.5, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    p = bollinger_pctb(close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 1 - buy_th, 1 - exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
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
        print(f"\n=== Bollinger %B buy<0.1 exit>0.5 — {mode_name}, 9코인 4년4국면 ===")
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
