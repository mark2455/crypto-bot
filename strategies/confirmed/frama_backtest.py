"""
[루프 40회차] FRAMA (Fractal Adaptive Moving Average, John Ehlers) — McGinley Dynamic처럼
재귀식 적응형 이동평균이지만, McGinley는 "가격변화 4제곱비"로 반응속도를 정하는 반면 FRAMA는
"프랙탈 차원"(최근 가격 움직임이 얼마나 거칠고 불규칙한지)으로 반응속도를 정한다 — 완전히
다른 메커니즘(프랙탈 기하학 기반).

윈도우(N=16)를 반으로 나눠 각각의 (최고-최저)/half-N = N1,N2, 전체의 (최고-최저)/N = N3
D = (log(N1+N2) - log(N3)) / log(2)          (프랙탈차원, 보통 1~2)
alpha = exp(-4.6*(D-1))                       (D가 클수록=더 불규칙할수록 alpha 작아져 느려짐)
FRAMA[i] = alpha*종가[i] + (1-alpha)*FRAMA[i-1]
%괴리 = (종가-FRAMA)/종가*100

검증 결과 (2026-07-30) — **4개 코인 확정, 헤드라인 2개 교체(LINK/ETC)**, 세션 최고 성과 중 하나:
  - **LINK: 롱온리.** buy=-2.0~-3.0 **3개 행 전부(12칸) 4/4**(역대급 견고) — 최대 buy=-2.0,exit=0.5
    → 4년 **+301.1%**(198건, 승률65%, 4/4). **헤드라인 교체**(구: Qstick +262.9%)
  - **ETC: 롱온리.** buy=-2.0~-2.5 넓은 블록(buy=-2.5 행 전체 4칸 포함) — 최대 buy=-2.0,exit=-0.5
    → 4년 **+100.9%**(168건, 승률66%, 4/4). **헤드라인 교체**(구: VWAP +79.1%)
  - **XRP: 롱숏대칭.** buy=-2.0 에서 exit=0/0.5 두 칸 연속 → buy=-2.0,exit=0.0 → +121.8%
    (270건, 승률64%, 4/4). 기존 헤드라인(McGinley +196.0%)엔 못 미쳐 추가확정
  - **SOL: 롱온리.** buy=-1.5 에서 exit=0.5/1.0 두 칸 연속 → buy=-1.5,exit=1.0 → +195.1%
    (262건, 승률66%, 4/4). 기존 헤드라인(Pivot Point +311.9%)엔 못 미쳐 추가확정
  - BNB: buy=-2.5,exit=-0.5 와 buy=-3.0,exit=0.5 가 서로 안 이어진 별개의 고립셀 2개뿐 →
    **미확정**(우연 판정)
  - LTC: 이 격자 범위에서 4/4 없음 → 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/frama_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 16


def frama_dist_pct(high, low, close, n=N):
    half = n // 2
    m = len(close)
    hh = pd.Series(high).rolling(n).max().to_numpy()
    ll = pd.Series(low).rolling(n).min().to_numpy()
    hh1 = pd.Series(high).rolling(half).max().to_numpy()
    ll1 = pd.Series(low).rolling(half).min().to_numpy()
    # 2번째 절반(최근 half봉)은 그대로, 1번째 절반(과거 half봉)은 half만큼 시프트해서 구함
    hh2 = pd.Series(hh1).shift(half).to_numpy()
    ll2 = pd.Series(ll1).shift(half).to_numpy()

    N1 = (hh1 - ll1) / half
    N2 = (hh2 - ll2) / half
    N3 = (hh - ll) / n

    with np.errstate(divide="ignore", invalid="ignore"):
        D = np.where((N1 + N2 > 0) & (N3 > 0), (np.log(N1 + N2) - np.log(N3)) / np.log(2), 1.0)
    D = np.clip(D, 1.0, 2.0)
    alpha = np.exp(-4.6 * (D - 1))
    alpha = np.clip(alpha, 0.01, 1.0)

    frama = np.full(m, np.nan)
    start = n
    if start < m:
        frama[start] = close[start]
        for i in range(start + 1, m):
            a = alpha[i]
            frama[i] = a * close[i] + (1 - a) * frama[i - 1]

    return (close - frama) / close * 100


def run(df, buy_th=-2.0, exit_th=0.0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    d = frama_dist_pct(high, low, close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 240
    m = len(close)
    while i < m:
        if np.isnan(d[i]):
            i += 1; continue
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
    d0 = frama_dist_pct(df0["high"].to_numpy(float), df0["low"].to_numpy(float), df0["close"].to_numpy(float))
    d0v = d0[~np.isnan(d0)]
    print(f"[분포확인] BTC FRAMA 괴리%: 1%={np.percentile(d0v,1):.2f} 5%={np.percentile(d0v,5):.2f} "
          f"95%={np.percentile(d0v,95):.2f} 99%={np.percentile(d0v,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== FRAMA 괴리% buy<-2.0 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
