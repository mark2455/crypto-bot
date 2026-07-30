"""
[루프 29회차] Qstick — 지금까지 쓴 지표는 전부 종가/고가/저가/거래량 기반이었는데, Qstick은
유일하게 "시가"를 사용한다. 매 봉의 (종가-시가), 즉 '캔들 몸통이 양봉인지 음봉인지'를
N봉 평균내어 최근 장중 매수/매도 압력의 평균적 방향을 측정. 기각된 BOP(Balance of Power,
봉 하나짜리 비율 (종가-시가)/(고가-저가))와 개념은 살짝 겹치지만, Qstick은 평활화된
절대크기 평균이라 계산식과 스케일이 다름.

Qstick = SMA(종가-시가, 14), z-score 정규화(코인간 스케일 보정)

검증 결과 (2026-07-30) — 3개 코인 확정, 코인별 최적 방향 다름:
  - **LINK: 롱온리.** buy=-1.75~-2.00 × exit=0~0.5 연속블록(4칸+) — 최대 buy=-1.5,exit=0.5
    → 4년 +262.9%(165건, 4/4). 롱숏은 3년차 -37%로 3/4 하락, 롱온리 채택
  - **BNB: 롱온리.** buy=-1.50~-2.50 × exit=-0.5~0 넓은 블록(8칸+) — 최대 buy=-1.5,exit=0.0
    → 4년 +84.7%(172건, 4/4). 롱숏은 +53.1%로 더 낮음
  - **DOT: 롱숏대칭이 더 우수.** buy=-1.75 행 전체(exit -0.5~0.5, 3칸) 4/4 — buy=-1.75,exit=0.0
    → 롱숏 4년 +176.2%(204건, 4/4), 롱온리는 같은 파라미터로도 4/4지만 +149.4%로 더 낮음
  - SOL: buy=-1.00,exit=0/0.5 와 buy=-1.75,exit=0 두 지점만 4/4, 그 사이(buy=-1.25,-1.50)는
    전부 3/4로 갈라진 갭 패턴 → **연속블록 아님, 미확정**(보수적 판정)

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/qstick_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def qstick_z(open_, close, n=14):
    body = close - open_
    q = pd.Series(body).rolling(n).mean()
    z = (q - q.rolling(200).mean()) / q.rolling(200).std()
    return z.to_numpy()


def run(df, buy_th=-1.5, exit_th=0.0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    open_ = df["open"].to_numpy(dtype=float)
    z = qstick_z(open_, close)
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
    z0 = qstick_z(df0["open"].to_numpy(dtype=float), df0["close"].to_numpy(dtype=float))
    z0v = z0[~np.isnan(z0)]
    print(f"[분포확인] BTC Qstick z: 1%={np.percentile(z0v,1):.2f} 5%={np.percentile(z0v,5):.2f} "
          f"95%={np.percentile(z0v,95):.2f} 99%={np.percentile(z0v,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== Qstick z buy<-1.5 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
