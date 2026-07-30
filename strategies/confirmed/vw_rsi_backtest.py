"""
[루프 53회차] Volume-Weighted RSI — 일반 RSI/CMO는 "가격변화의 크기"만으로 상승/하락일을
평균내는데, 이건 그 변화 크기에 **거래량까지 곱해서** 평균낸다. 기각된 MFI와는 다름: MFI는
전형가격의 방향만 분류하고 변화 크기는 아예 반영 안 하는데(tp*volume 그대로 합산), 이건
가격변화 크기(RSI의 gain/loss)를 그대로 살리면서 거래량 가중치만 추가.

delta = 종가[i]-종가[i-1]
gain = delta (delta>0) * 거래량,  loss = -delta (delta<0) * 거래량
VW-RSI = 100 * EMA(gain,14) / (EMA(gain,14)+EMA(loss,14))     0~100 유계

검증 결과 (2026-07-30) — **세션 최고 성과, DOT 헤드라인 교체(거래수·수익 둘 다 개선)**, 3코인 확정:
  - **DOT: 롱숏대칭.** buy=25 에서 exit=50~60 3칸 연속 4/4(견고) → 최대 buy=25,exit=60
    → 4년 **+438.2%**(357건, 승률69%, 4/4). **헤드라인 교체**(구: Keltner +340.7%, 206건 —
    거래수도 206→357건으로 늘고 수익도 더 높아진 전면 상위호환)
  - **LINK: 롱온리.** buy=20~35,exit=40 4칸 연속 + buy=25 행 대부분 → 최대 buy=25,exit=55
    → +171.9%(178건, 승률65%, 4/4). 헤드라인(FRAMA +301.1%)엔 못 미쳐 추가확정
  - **BNB: 롱온리.** buy=25 행 exit=40~50 3칸 연속 → buy=25,exit=45 → +38.2%(223건, 승률68%, 4/4).
    헤드라인(Weighted Close +132.9%)엔 못 미쳐 추가확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/vw_rsi_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 14


def vw_rsi(close, volume, n=N):
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta * volume, 0.0)
    loss = np.where(delta < 0, -delta * volume, 0.0)
    avg_gain = pd.Series(gain).ewm(span=n, adjust=False).mean()
    avg_loss = pd.Series(loss).ewm(span=n, adjust=False).mean()
    denom = avg_gain + avg_loss
    return (100 * avg_gain / denom).to_numpy()


def run(df, buy_th=25, exit_th=50, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    r = vw_rsi(close, vol, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 100 - buy_th, 100 - exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 220
    m = len(close)
    while i < m:
        if np.isnan(r[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (r[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (r[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if r[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and r[i] > sell_th and close[i] < ma200[i]:
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
    r0 = vw_rsi(df0["close"].to_numpy(dtype=float), df0["volume"].to_numpy(dtype=float))
    r0v = r0[~np.isnan(r0)]
    print(f"[분포확인] BTC VW-RSI: 1%={np.percentile(r0v,1):.1f} 5%={np.percentile(r0v,5):.1f} "
          f"50%={np.percentile(r0v,50):.1f} 95%={np.percentile(r0v,95):.1f} 99%={np.percentile(r0v,99):.1f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== VW-RSI buy<25 exit>50 — {mode_name}, 9코인 4년4국면 ===")
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
