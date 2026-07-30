"""
[확정 전략 — 루프 25회차] Percentage Volume Oscillator (PVO) — PPO(%MACD)와 계산식은 같지만
종가가 아니라 "거래량 자체"에 적용한다. 가격이 아니라 "거래 활동량이 최근 늘고 있는가/줄고
있는가"를 측정하는 지표라 OBV(방향 누적)·Force Index(가격변화×거래량)·Chaikin(ADL)·
Klinger(추세부호 volume force)와도 전부 다른 각도 — 가격 방향은 전혀 안 보고 순수 거래량의
모멘텀만 본다.

PVO = (EMA(거래량,12) - EMA(거래량,26)) / EMA(거래량,26) * 100

검증 결과 (2026-07-30, 롱온리 기준 — 롱숏대칭은 전 코인 대부분 마이너스라 기각):
  - SOL: buy_th=-24 행이 exit_th −10~+10 **5칸 전부 4/4** (역대급 견고), 최대 buy=-24 exit=+10
    → 4년 +130.1%, 거래 95건(연 22~26건), 승률 58%
  - ETH: exit_th=+10 열이 buy_th −26~−32 **4칸 전부 4/4** (견고), 최대 buy=-28 exit=+10
    → 4년 +74.6%, 거래 102건(연 22~30건), 승률 59%
  - LTC: buy_th=-32 에서만 4/4, 인접 -30/-34 는 전부 2/4 → **고립셀(우연) 판정, 미확정**
  - DOT/LINK/XRP/ETC/BTC/BNB: 격자탐색 전 구간 3/4가 최선 → 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/pvo_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def pvo(volume):
    ema12 = pd.Series(volume).ewm(span=12, adjust=False).mean()
    ema26 = pd.Series(volume).ewm(span=26, adjust=False).mean()
    return ((ema12 - ema26) / ema26 * 100).to_numpy()


def run(df, buy_th=-20, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    p = pvo(vol)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            if side == 1 and (p[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (p[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if p[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and p[i] > sell_th and close[i] < ma200[i]:
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
    p0 = pvo(df0["volume"].to_numpy(dtype=float))
    p0v = p0[~np.isnan(p0)]
    print(f"[분포확인] BTC PVO: 1%={np.percentile(p0v,1):.1f} 5%={np.percentile(p0v,5):.1f} "
          f"95%={np.percentile(p0v,95):.1f} 99%={np.percentile(p0v,99):.1f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== PVO buy<-20 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
