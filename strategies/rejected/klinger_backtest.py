"""
[루프 7회차] Klinger Volume Oscillator (KVO) — 거래량 기반, MFI(구간합)·Chaikin(누적ADL)과
또 다른 구성: 추세(상승/하락) 방향이 바뀔 때마다 누적값을 리셋하는 방식.

T(추세) = +1 if (고+저+종)>전봉 else -1
DM = 고가-저가
CM = 추세 유지시 CM전봉+DM, 추세전환시 DM전봉+DM (리셋)
VF(자금력) = 거래량 * |2*(DM/CM)-1| * T * 100
KVO = EMA(VF,34) - EMA(VF,55)
z = 롤링 정규화 (Chaikin에서 배운 보정)

실행:  ~/crypto-bot/venv/bin/python klinger_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def klinger_z(high, low, close, volume):
    hlc = high + low + close
    n = len(close)
    trend = np.ones(n)
    for i in range(1, n):
        trend[i] = 1.0 if hlc[i] > hlc[i - 1] else -1.0
    dm = high - low
    cm = np.zeros(n)
    cm[0] = dm[0]
    for i in range(1, n):
        if trend[i] == trend[i - 1]:
            cm[i] = cm[i - 1] + dm[i]
        else:
            cm[i] = dm[i - 1] + dm[i]
    ratio = np.divide(dm, cm, out=np.zeros_like(dm), where=cm != 0)
    vf = volume * np.abs(2 * ratio - 1) * trend * 100
    fast = pd.Series(vf).ewm(span=34, adjust=False).mean()
    slow = pd.Series(vf).ewm(span=55, adjust=False).mean()
    kvo = fast - slow
    z = (kvo - kvo.rolling(200).mean()) / kvo.rolling(200).std()
    return z.to_numpy()


def run(df, buy_th=-1.5, exit_th=0.0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    z = klinger_z(high, low, close, vol)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 410
    nlen = len(close)
    while i < nlen:
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
    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== Klinger VO z-score buy<-1.5 exit>0 — {mode_name}, 9코인 4년4국면 ===")
        for coin in COINS:
            df = load_candles_csv(f"data/{coin}_1h_4y.csv")
            pos = 0; yearly = []
            for start, end in PERIODS:
                mask = (df["time"] >= start) & (df["time"] < end)
                d = df[mask].reset_index(drop=True)
                if len(d) < 500:
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
