"""
[루프 22회차] Ehlers Center of Gravity (COG) Oscillator — 최근 N개 가격의 가중무게중심을
계산해 전환점을 최소지연으로 포착. Fisher Transform과 다른 Ehlers 지표지만 이번엔
'가격 대비 COG 괴리%'로 극단값+되돌림 방식에 맞게 구성(Fisher 실패 교훈 반영: 자기교차 금지).

COG = -(1*P0+2*P1+...+N*P(N-1)) / ΣP   (P0=최근값)
%괴리 = (종가-COG)/종가*100

실행:  ~/crypto-bot/venv/bin/python cog_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 10


def cog_dist_pct(close, n=N):
    """COG는 가격단위가 아니라 무게중심 '위치지수'(대략 -(N+1)/2 근방)이므로
    가격과 직접 합산하면 안 됨(이전 버그) — 자기 자신의 롤링 z-score 로 정규화."""
    weights = np.arange(1, n + 1)
    m = len(close)
    cog = np.full(m, np.nan)
    for i in range(n - 1, m):
        window = close[i - n + 1:i + 1][::-1]
        s = window.sum()
        if s != 0:
            cog[i] = -(weights * window).sum() / s
    s = pd.Series(cog)
    z = (s - s.rolling(200).mean()) / s.rolling(200).std()
    return z.to_numpy()


def run(df, buy_th=-1.5, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    d = cog_dist_pct(close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
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
    d0 = cog_dist_pct(df0["close"].to_numpy(dtype=float))
    d0v = d0[~np.isnan(d0)]
    print(f"[분포확인] BTC COG괴리%: 1%={np.percentile(d0v,1):.2f} 5%={np.percentile(d0v,5):.2f} "
          f"95%={np.percentile(d0v,95):.2f} 99%={np.percentile(d0v,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== COG 괴리% buy<-3 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
