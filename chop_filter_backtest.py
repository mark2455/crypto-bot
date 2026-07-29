"""
[루프 16회차] Choppiness Index 필터 + 확정전략(Connors RSI) 결합.
Choppiness Index 자체는 방향성 신호가 아니라 '지금이 횡보장(높은값)인지 추세장(낮은값)인지'
구분하는 레짐필터. Connors RSI가 대형코인(BTC/ETH)에서 탈락했던 건 '강한 상승추세라
타이밍전략이 그냥 보유보다 못했기 때문' — 그렇다면 '횡보장일 때만 거래'하도록 제한하면
대형코인에서도 개선될지 검증.

CHOP = 100*log10(Σ진범위N / (N기간 고가-저가)) / log10(N)   높을수록 횡보(비추세)

실행:  ~/crypto-bot/venv/bin/python chop_filter_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv
from connors_rsi_backtest import connors_rsi

FEE = 0.0004
MAX_HOLD = 100
BUY_TH, EXIT_TH = 10, 50
N = 14


def choppiness(high, low, close, n=N):
    prior_close = np.roll(close, 1); prior_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prior_close), np.abs(low - prior_close)))
    tr_sum = pd.Series(tr).rolling(n).sum().to_numpy()
    hh = pd.Series(high).rolling(n).max().to_numpy()
    ll = pd.Series(low).rolling(n).min().to_numpy()
    rng = hh - ll
    ratio = np.divide(tr_sum, rng, out=np.full_like(tr_sum, 1.0), where=rng != 0)
    return 100 * np.log10(ratio) / np.log10(n)


def run(df, chop_th=61.8, allow_short=True, use_chop=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    crsi = connors_rsi(close)
    chop = choppiness(high, low, close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 100 - BUY_TH, 100 - EXIT_TH

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            if side == 1 and (crsi[i] > EXIT_TH or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (crsi[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        chop_ok = (not use_chop) or (chop[i] > chop_th)
        if crsi[i] < BUY_TH and close[i] > ma200[i] and chop_ok:
            side, entry, held = 1, close[i], 0
        elif allow_short and crsi[i] > sell_th and close[i] < ma200[i] and chop_ok:
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
    print(f"=== Connors RSI + Choppiness필터(>61.8) vs 필터없음 — 9코인 4년4국면 ===\n")
    for coin in COINS:
        df = load_candles_csv(f"data/{coin}_1h_4y.csv")
        pos_f, pos_nf = 0, 0
        for start, end in PERIODS:
            mask = (df["time"] >= start) & (df["time"] < end)
            d = df[mask].reset_index(drop=True)
            if len(d) < 300:
                continue
            rf = run(d, use_chop=True)
            rnf = run(d, use_chop=False)
            if rf["return"] > 0: pos_f += 1
            if rnf["return"] > 0: pos_nf += 1
        r_full_f = run(df, use_chop=True)
        r_full_nf = run(df, use_chop=False)
        mark = "★" if pos_f == 4 else ""
        print(f"  {coin.replace('USDT',''):6} 필터있음 {r_full_f['return']:+8.2f}%({pos_f}/4){mark}  "
              f"필터없음 {r_full_nf['return']:+8.2f}%({pos_nf}/4)")


if __name__ == "__main__":
    main()
