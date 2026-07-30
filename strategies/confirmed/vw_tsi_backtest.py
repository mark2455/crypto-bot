"""
[루프 55회차] Volume-Weighted TSI — VW-RSI 성공 패턴(EMA 기반 평활 지표 + 거래량 가중은
통했음, VW-CMO처럼 롤링합 평활은 실패)을 같은 EMA 이중평활 방식인 TSI에 적용. 이미
DOT에서 확정된 TSI지만 거래량 가중을 추가하면 다른 코인/파라미터에서 새로 반응하는지 확인.

mom = 종가변화 * 거래량,  abs_mom = |종가변화| * 거래량
VW-TSI = 100 * EMA(EMA(mom,25),13) / EMA(EMA(abs_mom,25),13)

검증 결과 (2026-07-30) — EMA 이중평활이라 VW-RSI 패턴이 재현됨, BNB만 확정:
  - **BNB: 롱온리.** buy=-30~-35 × exit=0~10 2D블록 → 최대 buy=-30,exit=0
    → 4년 +87.6%(97건, 승률72%, 4/4). 헤드라인(Weighted Close +132.9%)엔 못 미쳐 추가확정
  - LINK: buy=-40,exit=-10 단일 고립셀만 4/4 → 미확정
  - ETC/SOL: 4/4 없음 → 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/vw_tsi_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def vw_tsi(close, volume, r=25, s=13):
    mom = np.diff(close, prepend=close[0]) * volume
    s1 = pd.Series(mom).ewm(span=r, adjust=False).mean()
    s2 = s1.ewm(span=s, adjust=False).mean()
    a1 = pd.Series(np.abs(mom)).ewm(span=r, adjust=False).mean()
    a2 = a1.ewm(span=s, adjust=False).mean()
    return (100 * s2 / a2).to_numpy()


def run(df, buy_th=-30, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    t = vw_tsi(close, vol)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 220
    m = len(close)
    while i < m:
        if np.isnan(t[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (t[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (t[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if t[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and t[i] > sell_th and close[i] < ma200[i]:
            side, entry, held = -1, close[i], 0
        i += 1

    if not trades:
        return {"trades": 0, "return": 0.0, "win_rate": 0.0}
    tt = np.array(trades)
    return {"trades": len(tt), "return": (np.prod(1 + tt) - 1) * 100, "win_rate": (tt > 0).mean() * 100}


COINS = ["DOTUSDT", "LTCUSDT", "LINKUSDT", "XRPUSDT", "ETCUSDT",
         "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
PERIODS = [("2022-07-30", "2023-07-30"), ("2023-07-30", "2024-07-30"),
           ("2024-07-30", "2025-07-30"), ("2025-07-30", "2026-07-29")]


def main():
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    t0 = vw_tsi(df0["close"].to_numpy(dtype=float), df0["volume"].to_numpy(dtype=float))
    t0v = t0[~np.isnan(t0)]
    print(f"[분포확인] BTC VW-TSI: 1%={np.percentile(t0v,1):.1f} 5%={np.percentile(t0v,5):.1f} "
          f"50%={np.percentile(t0v,50):.1f} 95%={np.percentile(t0v,95):.1f} 99%={np.percentile(t0v,99):.1f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== VW-TSI buy<-30 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
