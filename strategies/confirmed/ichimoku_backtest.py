"""
[루프 12회차-2] Ichimoku 구름대 중심선 괴리 — 원래는 전환선/기준선 크로스오버 방식이나
(이미 실패 검증된 크로스오버 계열), 대신 구름대(선행스팬A/B 평균) 대비 현재가 괴리%로
극단값+되돌림 방식에 맞게 변형.

전환선(9) = (9기간고+9기간저)/2, 기준선(26) = (26기간고+26기간저)/2
선행스팬A = (전환선+기준선)/2, 선행스팬B = (52기간고+52기간저)/2
구름중심 = (스팬A+스팬B)/2  (미래이동 없이 현재값 사용, lookahead 방지)
%괴리 = (종가-구름중심)/종가*100

실행:  ~/crypto-bot/venv/bin/python ichimoku_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def cloud_dist_pct(high, low, close):
    def mid(n):
        h = pd.Series(high).rolling(n).max()
        l = pd.Series(low).rolling(n).min()
        return (h + l) / 2
    tenkan, kijun = mid(9), mid(26)
    span_a = (tenkan + kijun) / 2
    span_b = mid(52)
    cloud_mid = (span_a + span_b) / 2
    return ((pd.Series(close) - cloud_mid) / close * 100).to_numpy()


def run(df, buy_th=-5, exit_th=0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    d = cloud_dist_pct(high, low, close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if side != 0:
            held += 1
            if side == 1 and (d[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (d[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if d[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and d[i] > sell_th and close[i] < ma200[i]:
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
        print(f"\n=== Ichimoku 구름중심 괴리% buy<-5 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
