"""
[루프 1회차] Ehlers Laguerre RSI — 4단 라게르 필터 기반, 표준 RSI보다 지연이 적다고 알려진
덜 알려진 지표. Wilder RSI(단순 지수평활)와 달리 재귀형 라게르 필터 4단 캐스케이드를 사용.

공식(Ehlers 원안):
  L0 = (1-γ)*price + γ*L0[전봉]
  L1 = -γ*L0 + L0[전봉] + γ*L1[전봉]
  L2 = -γ*L1 + L1[전봉] + γ*L2[전봉]
  L3 = -γ*L2 + L2[전봉] + γ*L3[전봉]
  CU = Σmax(L0-L1,0)+max(L1-L2,0)+max(L2-L3,0)
  CD = Σmax(L1-L0,0)+max(L2-L1,0)+max(L3-L2,0)
  LRSI = CU/(CU+CD)   (0~1 범위, 표준 RSI의 0~100과 다름)

Connors RSI 와 동일 골격으로 비교: 롱(과매도+상승추세)/숏(과매수+하락추세), 추세필터 MA200.

실행:  ~/crypto-bot/venv/bin/python laguerre_rsi_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
GAMMA = 0.5


def laguerre_rsi(close, gamma=GAMMA):
    n = len(close)
    L0 = np.zeros(n); L1 = np.zeros(n); L2 = np.zeros(n); L3 = np.zeros(n)
    lrsi = np.zeros(n)
    for i in range(1, n):
        L0[i] = (1 - gamma) * close[i] + gamma * L0[i - 1]
        L1[i] = -gamma * L0[i] + L0[i - 1] + gamma * L1[i - 1]
        L2[i] = -gamma * L1[i] + L1[i - 1] + gamma * L2[i - 1]
        L3[i] = -gamma * L2[i] + L2[i - 1] + gamma * L3[i - 1]
        cu = max(L0[i] - L1[i], 0) + max(L1[i] - L2[i], 0) + max(L2[i] - L3[i], 0)
        cd = max(L1[i] - L0[i], 0) + max(L2[i] - L1[i], 0) + max(L3[i] - L2[i], 0)
        lrsi[i] = cu / (cu + cd) if (cu + cd) > 0 else 0.5
    return lrsi


def run(df, buy_th=0.15, exit_th=0.85, allow_short=True, gamma=GAMMA):
    close = df["close"].to_numpy(dtype=float)
    lrsi = laguerre_rsi(close, gamma)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 1 - buy_th, 1 - exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            if side == 1 and (lrsi[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (lrsi[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if lrsi[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and lrsi[i] > sell_th and close[i] < ma200[i]:
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
        print(f"\n=== Laguerre RSI(γ={GAMMA}) buy<{0.15} exit>{0.85} — {mode_name}, 9코인 4년4국면 ===")
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
