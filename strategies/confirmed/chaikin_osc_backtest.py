"""
[루프 6회차-2] Chaikin Oscillator — 누적 자금흐름선(ADL)에 MACD(3,10)를 적용.
MFI(구간합)와 달리 '누적' 방식이라 코인마다 스케일이 크게 다름 → 롤링 z-score로 정규화해서
극단값+되돌림 방식 적용 (Ultimate Oscillator 사고에서 배운 보정 방법).

MFM = ((종가-저가)-(고가-종가))/(고가-저가)
ADL = cumsum(MFM * 거래량)
ChaikinOsc = EMA(ADL,3) - EMA(ADL,10)
z = (ChaikinOsc - 롤링평균200) / 롤링표준편차200   ← 정규화, 코인 무관 비교 가능

실행:  ~/crypto-bot/venv/bin/python chaikin_osc_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def chaikin_z(high, low, close, volume):
    rng = high - low
    mfm = np.divide((close - low) - (high - close), rng, out=np.zeros_like(rng), where=rng != 0)
    mfv = mfm * volume
    adl = np.cumsum(mfv)
    fast = pd.Series(adl).ewm(span=3, adjust=False).mean()
    slow = pd.Series(adl).ewm(span=10, adjust=False).mean()
    osc = (fast - slow)
    z = (osc - osc.rolling(200).mean()) / osc.rolling(200).std()
    return z.to_numpy()


def run(df, buy_th=-1.5, exit_th=0.0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    z = chaikin_z(high, low, close, vol)
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
        print(f"\n=== Chaikin Osc z-score buy<-1.5 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
