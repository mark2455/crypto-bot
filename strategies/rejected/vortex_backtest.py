"""
[루프 6회차] Vortex Indicator — 상승/하락 '소용돌이 운동량'을 각각 측정해 비교.
VM+ = |고가 - 전봉저가|, VM- = |저가 - 전봉고가|, TR=진범위
VI+ = ΣVM+/ΣTR, VI- = ΣVM-/ΣTR   (N기간)
VIdiff = VI+ - VI-  (자기교차 아닌 서로 다른 두 계열의 차이 → 극단값+되돌림 방식 적용)

실행:  ~/crypto-bot/venv/bin/python vortex_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 14


def vortex_diff(high, low, close, n=N):
    prior_close = np.roll(close, 1); prior_close[0] = close[0]
    prior_low = np.roll(low, 1); prior_low[0] = low[0]
    prior_high = np.roll(high, 1); prior_high[0] = high[0]
    vm_plus = np.abs(high - prior_low)
    vm_minus = np.abs(low - prior_high)
    tr = np.maximum(high - low, np.maximum(np.abs(high - prior_close), np.abs(low - prior_close)))
    vm_plus_sum = pd.Series(vm_plus).rolling(n).sum().to_numpy()
    vm_minus_sum = pd.Series(vm_minus).rolling(n).sum().to_numpy()
    tr_sum = pd.Series(tr).rolling(n).sum().to_numpy()
    vi_plus = np.divide(vm_plus_sum, tr_sum, out=np.zeros_like(vm_plus_sum), where=tr_sum != 0)
    vi_minus = np.divide(vm_minus_sum, tr_sum, out=np.zeros_like(vm_minus_sum), where=tr_sum != 0)
    return vi_plus - vi_minus


def run(df, buy_th=-0.15, exit_th=0.0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    vd = vortex_diff(high, low, close, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    nlen = len(close)
    while i < nlen:
        if side != 0:
            held += 1
            if side == 1 and (vd[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (vd[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if vd[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and vd[i] > sell_th and close[i] < ma200[i]:
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
    vd0 = vortex_diff(df0["high"].to_numpy(float), df0["low"].to_numpy(float), df0["close"].to_numpy(float))
    print(f"[분포확인] BTC VIdiff: 1%={np.percentile(vd0,1):.3f} 5%={np.percentile(vd0,5):.3f} "
          f"95%={np.percentile(vd0,95):.3f} 99%={np.percentile(vd0,99):.3f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== Vortex diff buy<-0.15 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
