"""
[루프 35회차] Ulcer Index (Peter Martin) — 지금까지 쓴 지표는 전부 "가격이 위/아래 어디로
가는가"를 봤는데, 이건 유일하게 "최근 고점 대비 얼마나 깊고 오래 하락 중인가"(하락폭의
RMS)만 측정 — 변동성이 아니라 '고통(pain)'의 크기. 단독으로는 항상 0 이상(단봉성)이라,
그 자체의 롤링 z-score를 취해 "지금 고통이 평소보다 유난히 심한가/약한가"를 양방향 신호로 씀.

drawdown% = (종가-최근N봉최고가)/최근N봉최고가*100   (항상 ≤0)
UlcerIndex = sqrt(mean(drawdown%^2, N))              (항상 ≥0, 값이 클수록 깊은 고통)
z = (UI - 롤링평균200) / 롤링표준편차200

검증 결과 (2026-07-30):
  - **SOL: 롱온리.** buy=-1.5 행(exit -0.5~0.5 3칸) + buy=-1.25 행(exit 0~0.5 2칸) 이 서로
    맞닿은 넓은 연속블록(7칸+) — 최대 buy=-1.25,exit=0.0 → 4년 **+306.1%**(128건, 4/4).
    **헤드라인 교체**(구: VWAP +235.7%). **주의: 승률 45.3%로 다른 확정 전략들(대부분 60~90%대)
    보다 훨씬 낮음** — 자주 잃되 이길 때 크게 이기는 비대칭 구조. 리스크 성격이 다르다는 점을
    반드시 인지할 것
  - DOT: buy=-1.50,exit=0.0 단일 고립셀만 4/4(사방 전부 1~3/4) → **미확정**(우연 판정)
  - BTC/ETH: 이 격자 범위에서 4/4 없음(최대 3/4) → 미확정 (BTC는 억지로 겨냥하지 않음)

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/ulcer_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 14


def ulcer_z(close, n=N):
    c = pd.Series(close, dtype=float)
    roll_max = c.rolling(n).max()
    dd = (c - roll_max) / roll_max * 100
    ui = (dd ** 2).rolling(n).mean().pow(0.5)
    z = (ui - ui.rolling(200).mean()) / ui.rolling(200).std()
    return z.to_numpy()


def run(df, buy_th=-1.5, exit_th=0.0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    z = ulcer_z(close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 220
    n = len(close)
    while i < n:
        if np.isnan(z[i]):
            i += 1; continue
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
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    z0 = ulcer_z(df0["close"].to_numpy(dtype=float))
    z0v = z0[~np.isnan(z0)]
    print(f"[분포확인] BTC Ulcer z: 1%={np.percentile(z0v,1):.2f} 5%={np.percentile(z0v,5):.2f} "
          f"95%={np.percentile(z0v,95):.2f} 99%={np.percentile(z0v,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== Ulcer z buy<-1.5 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
