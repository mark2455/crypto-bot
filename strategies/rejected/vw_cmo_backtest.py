"""
[루프 54회차] Volume-Weighted CMO — 방금 성공한 VW-RSI와 같은 아이디어(가격변화 크기에
거래량 가중치 추가)를, RSI와는 다른 평활방식(EMA 아닌 고정윈도우 롤링합)을 쓰는 CMO에
적용. CMO는 이미 LINK/XRP에서 확정된 지표지만, 거래량을 안 쓰는 원본과 달리 이번엔
가격변화×거래량을 롤링합산 — 다른 코인에서 새로 반응할 수 있는지 확인.

delta = 종가변화, up = delta(양수만)*거래량, down = -delta(음수만)*거래량
VW-CMO = 100 * (rolling_sum(up,N) - rolling_sum(down,N)) / (rolling_sum(up,N)+rolling_sum(down,N))
-100~100 유계

실행:  ~/crypto-bot/venv/bin/python vw_cmo_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 14


def vw_cmo(close, volume, n=N):
    delta = np.diff(close, prepend=close[0])
    up = np.clip(delta, 0, None) * volume
    down = np.clip(-delta, 0, None) * volume
    su = pd.Series(up).rolling(n).sum().to_numpy()
    sd = pd.Series(down).rolling(n).sum().to_numpy()
    denom = su + sd
    return np.where(denom > 0, 100 * (su - sd) / denom, 0.0)


def run(df, buy_th=-50, exit_th=0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    c = vw_cmo(close, vol, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 220
    m = len(close)
    while i < m:
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
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    c0 = vw_cmo(df0["close"].to_numpy(dtype=float), df0["volume"].to_numpy(dtype=float))
    print(f"[분포확인] BTC VW-CMO: 1%={np.percentile(c0,1):.1f} 5%={np.percentile(c0,5):.1f} "
          f"50%={np.percentile(c0,50):.1f} 95%={np.percentile(c0,95):.1f} 99%={np.percentile(c0,99):.1f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== VW-CMO buy<-50 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
