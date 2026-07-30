"""
[루프 34회차] Linear Regression Channel z-score — 최근 N봉에 최소제곱 회귀직선을 매번
새로 피팅하고, 현재가가 그 추세선에서 얼마나(회귀 잔차의 표준편차 대비) 벗어나 있는지 측정.
McGinley(적응형 이동평균)나 HMA(WMA 트릭)와 달리 "이동평균"이 아니라 매 시점 독립적으로
최소제곱 직선을 다시 긋는 방식이라 완전히 다른 계산 메커니즘. BTC처럼 변동성이 낮고 추세가
매끈한 자산에서 특히 다르게 작동할 수 있어 시도.

회귀직선을 rolling sum 공식으로 벡터화(느린 rolling.apply 대신 O(n) 속도):
  S_xy = RS(t*y) - (T-n+1)*RS(y),  Sx=n(n-1)/2, Sxx=(n-1)n(2n-1)/6 (윈도우 내 고정)
  slope = (n*S_xy - Sx*RS_y) / (n*Sxx - Sx^2),  intercept = (RS_y - slope*Sx)/n
  예측값(현재점) = intercept + slope*(n-1)
  잔차표준편차 = sqrt(SS_res/n),  z = (종가-예측값)/잔차표준편차

검증 결과 (2026-07-30) — BTC를 특히 겨냥해서 넓은 범위로 격자탐색했으나 BTC는 이번에도
최대 2/4에 그쳐 못 잡음(여전히 KST가 BTC 대표). 대신 2개 코인만 확정(둘 다 추가확정, 헤드라인 변화 없음):
  - **LINK: 롱온리.** buy=-2.00 에서 exit=0/0.5 두 칸 연속 4/4(얇지만 인접, 고립셀 아님)
    → 최대 buy=-2.0,exit=0.0 → 4년 +97%(4/4)
  - **BNB: 롱온리.** exit=-0.5 열이 buy -1.75~-2.25 3칸 연속 4/4 → 최대 buy=-2.25,exit=-0.5
    → 4년 +40%(4/4)
  - DOT/XRP/ETC: 산발적 3/4 또는 체커보드(예: XRP buy=-3.0 exit=-0.5/+0.5만 ★, 사이 exit=0은
    3/4로 실패) → 미확정
  - SOL: buy=-2.25,exit=1.0 단일 고립셀만 4/4 → 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/linreg_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 20


def linreg_z(close, n=N):
    y = pd.Series(close, dtype=float)
    t = np.arange(len(y), dtype=float)
    ty = t * y.to_numpy()

    RS_y = y.rolling(n).sum()
    RS_yy = (y ** 2).rolling(n).sum()
    RS_ty = pd.Series(ty).rolling(n).sum()

    Sx = n * (n - 1) / 2
    Sxx = (n - 1) * n * (2 * n - 1) / 6
    T = t  # 현재 인덱스(윈도우 끝)
    t_start = T - n + 1

    S_xy = RS_ty.to_numpy() - t_start * RS_y.to_numpy()
    denom = (n * Sxx - Sx ** 2)
    slope = (n * S_xy - Sx * RS_y.to_numpy()) / denom
    intercept = (RS_y.to_numpy() - slope * Sx) / n
    predicted = intercept + slope * (n - 1)

    SS_res = (RS_yy.to_numpy() - 2 * intercept * RS_y.to_numpy() - 2 * slope * S_xy
              + n * intercept ** 2 + 2 * intercept * slope * Sx + slope ** 2 * Sxx)
    std_err = np.sqrt(np.maximum(SS_res, 0) / n)

    dev = y.to_numpy() - predicted
    z = np.divide(dev, std_err, out=np.zeros_like(dev), where=std_err > 1e-12)
    return z


def run(df, buy_th=-2.0, exit_th=0.0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    z = linreg_z(close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    m = len(close)
    while i < m:
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
    z0 = linreg_z(df0["close"].to_numpy(dtype=float))
    z0v = z0[~np.isnan(z0)]
    print(f"[분포확인] BTC LinReg z: 1%={np.percentile(z0v,1):.2f} 5%={np.percentile(z0v,5):.2f} "
          f"95%={np.percentile(z0v,95):.2f} 99%={np.percentile(z0v,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== LinReg z buy<-2.0 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
