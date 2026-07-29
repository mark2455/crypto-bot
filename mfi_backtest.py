"""
[루프 4회차] Money Flow Index (MFI) — RSI에 거래량을 가중한 지표.
지금까지 시도한 모든 지표 중 유일하게 '거래량'을 반영. Connors RSI/CMO와 같은
'극단값 도달 후 되돌림' 방식(자기교차 방식 아님 — Fisher/RVI가 실패한 이유 회피).

TP(전형가격) = (고가+저가+종가)/3
RMF(원시자금흐름) = TP * 거래량
N기간 중 TP상승일의 RMF합 = 긍정자금흐름, TP하락일의 RMF합 = 부정자금흐름
MFI = 100 - 100/(1 + 긍정/부정)   (0~100, RSI와 같은 스케일)

신호: 롱(MFI<buy_th 과매도 + 가격>MA200) / 숏(MFI>sell_th 과매수 + 가격<MA200)
청산: 반대 임계값 또는 MAX_HOLD.

실행:  ~/crypto-bot/venv/bin/python mfi_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 14


def mfi(high, low, close, volume, n=N):
    tp = (high + low + close) / 3
    rmf = tp * volume
    delta = np.diff(tp, prepend=tp[0])
    pos = np.where(delta > 0, rmf, 0.0)
    neg = np.where(delta < 0, rmf, 0.0)
    pos_sum = pd.Series(pos).rolling(n).sum().to_numpy()
    neg_sum = pd.Series(neg).rolling(n).sum().to_numpy()
    ratio = np.divide(pos_sum, neg_sum, out=np.full_like(pos_sum, np.inf), where=neg_sum != 0)
    return 100 - 100 / (1 + ratio)


def run(df, buy_th=20, exit_th=50, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    m = mfi(high, low, close, vol, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 100 - buy_th, 100 - exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    nlen = len(close)
    while i < nlen:
        if side != 0:
            held += 1
            if side == 1 and (m[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (m[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if m[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and m[i] > sell_th and close[i] < ma200[i]:
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
        print(f"\n=== MFI(N={N}) buy<20 exit>50 — {mode_name}, 9코인 4년4국면 ===")
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
