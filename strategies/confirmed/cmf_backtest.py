"""
[루프 59회차] Chaikin Money Flow (CMF) — Marc Chaikin.
"일정 기간 동안의 매수압력 대 매도압력 비율"을 -1~+1로 정규화한 지표.
같은 저자의 Chaikin Oscillator(누적 ADL의 EMA3-EMA10 차이, 추세형)나 raw ADL(단순 누적, 기각됨)과
전부 다른 계산식 — CMF는 "누적"이 아니라 최근 N봉 구간의 MFV 합을 그 구간 거래량 합으로 "나눠서"
자체 정규화한다(추가 z-score 불필요, 자연 유계).

MFM(자금흐름승수) = ((종가-저가)-(고가-종가)) / (고가-저가)     [-1, +1] 유계
MFV(자금흐름거래량) = MFM * 거래량
CMF = 롤링합(MFV, 20) / 롤링합(거래량, 20)                      [-1, +1] 유계, N=20(약 20시간)

CMF가 매우 낮음 = 최근 매도압력이 지배적(분산/투매) → 반등 기대. 반대는 매수압력 과열 → 되돌림 기대.
MA200 추세필터로 방향 제한, 평균회귀 시 청산.

검증 결과 (2026-07-30, 롱숏대칭 기준):
  - ETH: buy_th −0.30~−0.25 × exit_th 0.05~0.10 **2D 견고 블록**(5칸, 코너 1칸(-0.25,0.00)=3/4 만 갭)
    최적 buy=−0.25 exit=0.10 → 4년 +70.92%, 거래 102건, 승률 66.7% (전 연도 플러스)
  - XRP 롱온리: buy=−0.25 고정, exit −0.05~0.00 2칸만 4/4 → 기존 4칸 기준 미달로 미확정
  - DOT 롱숏: (−0.30,−0.05)·(−0.15,0.10) 2개 고립셀, 체커보드 패턴 → 기각
  - 나머지 6코인: 4/4 없음 또는 고립셀 1개뿐 → 미확정
  - ETH 기존 대표(Coppock Curve +166.7%)보다 낮아 헤드라인 교체 없음 — 추가 확정 지표로 등재

실행:  PYTHONPATH=. ~/crypto-bot/venv/bin/python strategies/confirmed/cmf_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 20


def cmf(high, low, close, volume, n=N):
    rng = np.where(high > low, high - low, 1e-9)
    mfm = ((close - low) - (high - close)) / rng
    mfv = mfm * volume
    return (pd.Series(mfv).rolling(n).sum() / pd.Series(volume).rolling(n).sum()).to_numpy()


def run(df, buy_th=-0.25, exit_th=0.10, allow_short=True):
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    c = cmf(high, low, close, vol)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if np.isnan(c[i]) or np.isnan(ma200[i]):
            i += 1; continue
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


def grid_search(coin, allow_short):
    df = load_candles_csv(f"data/{coin}_1h_4y.csv")
    buy_ths = [-0.30, -0.25, -0.20, -0.15, -0.10]
    exit_ths = [-0.10, -0.05, 0.0, 0.05, 0.10]
    grid = {}
    for b in buy_ths:
        for e in exit_ths:
            pos = 0
            for start, end in PERIODS:
                mask = (df["time"] >= start) & (df["time"] < end)
                d = df[mask].reset_index(drop=True)
                if len(d) < 500:
                    continue
                r = run(d, buy_th=b, exit_th=e, allow_short=allow_short)
                if r["return"] > 0:
                    pos += 1
            grid[(b, e)] = pos
    return grid, buy_ths, exit_ths


def main():
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    c0 = cmf(df0["high"].to_numpy(dtype=float), df0["low"].to_numpy(dtype=float),
             df0["close"].to_numpy(dtype=float), df0["volume"].to_numpy(dtype=float))
    c0v = c0[~np.isnan(c0)]
    print(f"[분포확인] BTC CMF: 1%={np.percentile(c0v,1):.3f} 5%={np.percentile(c0v,5):.3f} "
          f"95%={np.percentile(c0v,95):.3f} 99%={np.percentile(c0v,99):.3f}\n")

    for coin in COINS:
        for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
            grid, buy_ths, exit_ths = grid_search(coin, allow_short)
            best = max(grid.items(), key=lambda kv: kv[1])
            if best[1] == 4:
                hits = [k for k, v in grid.items() if v == 4]
                print(f"{coin.replace('USDT',''):6} {mode_name}: 4/4 히트 {len(hits)}개 -> {hits}")
            else:
                print(f"{coin.replace('USDT',''):6} {mode_name}: 최고 {best[1]}/4 @ {best[0]}")


if __name__ == "__main__":
    main()
