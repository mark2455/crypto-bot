"""
[루프 32회차] McGinley Dynamic (John McGinley) — HMA(이중 WMA로 지연을 줄이는 트릭)와 달리,
가격이 빠르게 움직이면 스스로 더 빠르게 따라가고 느리게 움직이면 더 느려지는 "재귀식 적응형"
이동평균. 일반 EMA/WMA는 고정된 가중치인데, 이건 매 봉마다 (직전값 대비 현재가 비율)^4 로
반응속도 자체가 바뀐다 — 지금까지 쓴 어떤 이동평균 계열과도 계산 메커니즘이 다름.

MD[0] = 종가[0]
MD[i] = MD[i-1] + (종가[i]-MD[i-1]) / (N * (종가[i]/MD[i-1])^4)     (N=10)
%괴리 = (종가-MD)/종가*100

검증 결과 (2026-07-30) — 5개 코인 확정(이번 세션 최다), 세밀한 격자탐색으로 고립셀 여러 개 걸러냄:
  - **XRP: 롱숏대칭.** buy=-2.0 행이 exit -1~1 3칸 연속 4/4 — 최대 buy=-2.0,exit=0
    → 4년 +196.0%(4/4). **헤드라인 교체** (구: Ichimoku +77.4%)
  - **DOT: 롱온리.** buy=-2.0~-5.0 × exit=-1~0 12칸 전부 4/4(역대급 견고) — 최대
    buy=-3.5,exit=2 → +145.0%(4/4). 기존 헤드라인(Keltner +340.7%)엔 못 미쳐 추가 확정으로만 기록
  - **LINK: 롱온리.** buy=-4.0 행 전체(exit 4칸 전부) 4/4 — 최대 buy=-4.0,exit=2 → +60%(4/4).
    (주의: buy=-3.0,exit=0 도 4/4로 나왔으나 사방이 전부 3/4인 고립셀이라 제외 — 초기 기본값 테스트에
    이 고립셀이 걸려서 착오가 있었음, 재검증으로 정정)
  - **BNB: 롱온리.** exit=-1 열이 buy -2.0~-3.5 4칸 연속 4/4 — 최대 buy=-2.0,exit=-1 → +59%(4/4)
  - **SOL: 롱온리.** buy∈{-3.0,-3.5}×exit=1 소규모 클러스터(3칸) — 최대 buy=-3.5,exit=1 → +40%(4/4)
  - LTC: 이 격자 범위에서 견고한 4/4 없음 → 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/mcginley_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 10


def mcginley(close, n=N):
    md = np.empty_like(close)
    md[0] = close[0]
    for i in range(1, len(close)):
        ratio = close[i] / md[i - 1]
        denom = n * (ratio ** 4)
        md[i] = md[i - 1] + (close[i] - md[i - 1]) / denom
    return md


def mcginley_dist_pct(close, n=N):
    md = mcginley(close, n)
    return (close - md) / close * 100


def run(df, buy_th=-3, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    d = mcginley_dist_pct(close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
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
    d0 = mcginley_dist_pct(df0["close"].to_numpy(dtype=float))
    print(f"[분포확인] BTC McGinley 괴리%: 1%={np.percentile(d0,1):.2f} 5%={np.percentile(d0,5):.2f} "
          f"95%={np.percentile(d0,95):.2f} 99%={np.percentile(d0,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== McGinley 괴리% buy<-3 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
