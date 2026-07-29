"""
[루프 2회차] Chande Momentum Oscillator (CMO) — RSI와 달리 평활화(스무딩) 없이
N기간 상승분 합/하락분 합을 그대로 비교. 더 반응이 빠르고 노이즈에 민감하다고 알려짐.

CMO = 100 * (Su - Sd) / (Su + Sd)   (Su,Sd = N기간 상승폭/하락폭의 단순 합, 평활화 없음)
범위 -100~+100.

Connors RSI 와 동일 골격: 롱(과매도+상승추세)/숏(과매수+하락추세), MA200 추세필터.

실행:  ~/crypto-bot/venv/bin/python cmo_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 14


def cmo(close, n=N):
    delta = np.diff(close, prepend=close[0])
    up = np.clip(delta, 0, None)
    down = np.clip(-delta, 0, None)
    su = pd.Series(up).rolling(n).sum().to_numpy()
    sd = pd.Series(down).rolling(n).sum().to_numpy()
    denom = su + sd
    return np.where(denom > 0, 100 * (su - sd) / denom, 0.0)


def run(df, buy_th=-50, exit_th=0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    c = cmo(close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    nlen = len(close)
    while i < nlen:
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


def main():
    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== CMO(N={N}) buy<-50 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
