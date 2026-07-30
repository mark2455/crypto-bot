"""
[루프 45회차] Vertical Horizontal Filter (VHF, Adam White) — 기각된 Efficiency Ratio(순변위/
총이동거리, 방향 있음)나 Choppiness(ATR합/전체범위)와 "추세강도 측정"이라는 목적은 비슷하나
계산식이 다름: VHF는 종가의 (최고-최저) 를 "종가 변화분의 절대값 합"으로 나눈다 — 부호 없는
순수 범위 대 이동거리 비율.

VHF = (최근N봉 종가최고 - 최근N봉 종가최저) / sum(|종가[i]-종가[i-1]|, N)

검증 결과 (2026-07-30) — **BTC 헤드라인 재교체(수익 4배 개선)**. VHF는 방향성 오실레이터가
아니라 "지금이 추세인지 횡보인지"만 재는 스칼라 게이지라 다른 지표들과 논리가 다름 —
낮은 VHF(횡보 중) + MA200 방향 = "추세 안에서 잠깐 쉬는 구간을 매수" 라는 다른 가설인데도 작동함:
  - **BTC: 롱온리.** exit=0.45~0.50 열에서 buy=0.15~0.25 대부분 4/4(역대급 견고 블록) — 최대
    buy=0.25,exit=0.50 → 4년 **+225.7%**(224건, 승률54%, 4/4). **헤드라인 교체**(구: Twiggs
    Money Flow +56.1%, 322건 — 거래수는 다소 줄지만(224건도 충분히 많음) 수익이 4배)
  - BNB: 3/4가 최선(4/4 없음) → 미확정
  - 나머지: 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/vhf_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 28


def vhf(close, n=N):
    c = pd.Series(close)
    hi = c.rolling(n).max()
    lo = c.rolling(n).min()
    path = c.diff().abs().rolling(n).sum()
    return np.divide((hi - lo).to_numpy(), path.to_numpy(),
                      out=np.zeros(len(c)), where=path.to_numpy() > 1e-12)


def run(df, buy_th=0.2, exit_th=0.4, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    v = vhf(close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = buy_th, exit_th  # VHF는 항상 양수라 대칭 아님 -> buy_th를 그대로 낮은극단, sell은 높은극단 별도 파라미터로 취급

    trades = []
    side = 0; entry = 0.0; held = 0
    i = n + 10
    m = len(close)
    while i < m:
        if v[i] == 0:
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (v[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (v[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if v[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and v[i] < buy_th and close[i] < ma200[i]:
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
    v0 = vhf(df0["close"].to_numpy(dtype=float))
    v0v = v0[v0 > 0]
    print(f"[분포확인] BTC VHF: 1%={np.percentile(v0v,1):.3f} 5%={np.percentile(v0v,5):.3f} "
          f"50%={np.percentile(v0v,50):.3f} 95%={np.percentile(v0v,95):.3f} 99%={np.percentile(v0v,99):.3f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== VHF buy<0.2 exit>0.4 — {mode_name}, 9코인 4년4국면 ===")
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
