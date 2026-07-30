"""
[루프 62회차] ADX/DMI (Average Directional Index / Directional Movement Index) — J. Welles Wilder.
Vortex Indicator(VM+ = |고가-전봉저가|, VM- = |저가-전봉고가|, 단순합산)와 방향성 지표라는 큰 틀은
비슷하지만 DM(방향성 움직임) 정의 자체가 다르고(상승폭 vs 하락폭을 직접 비교해 더 큰 쪽만 채택),
True Range로 정규화 후 Wilder 고유의 지수평활(alpha=1/14)을 사용 — Vortex는 단순 롤링합만 사용.

+DM = max(고가[i]-고가[i-1], 0)  단, (고가[i]-고가[i-1]) > (저가[i-1]-저가[i]) 일 때만 채택
-DM = max(저가[i-1]-저가[i], 0)  단, 반대 조건일 때만 채택
+DI = 100 * Wilder평활(+DM) / Wilder평활(TR)
-DI = 100 * Wilder평활(-DM) / Wilder평활(TR)
DI_diff = +DI - -DI   (자연스레 0 중심, 방향성 우위를 직접 비교)

검증 결과 (2026-07-30, 롱온리 기준):
  - BNB: buy_th −25.0~−20.0 두 행 전체(exit 5칸×2행=10칸) **역대급 넓은 2D 블록**
    (인접 buy −30/−15 도 절벽 없이 2~3/4로 완만히 감소) → buy=−20.0,exit=0.0 →
    4년 +46.63%, 거래 76건, 승률 69.7% (전 연도 플러스)
  - DOT 롱숏: buy=−25.0 행 전체 4/4 (부가 확정 후보, 문서엔 BNB만 기록)
  - BNB 기존 대표(Weighted Close +132.9%)보다 낮아 헤드라인 교체 없음 — 추가 확정 지표로 등재

실행:  PYTHONPATH=. ~/crypto-bot/venv/bin/python strategies/confirmed/adx_dmi_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 14


def _wilder(x, n=N):
    return pd.Series(x).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def di_diff(high, low, close, n=N):
    prior_close = np.roll(close, 1); prior_close[0] = close[0]
    prior_high = np.roll(high, 1); prior_high[0] = high[0]
    prior_low = np.roll(low, 1); prior_low[0] = low[0]

    up_move = high - prior_high
    down_move = prior_low - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = np.maximum(high - low, np.maximum(np.abs(high - prior_close), np.abs(low - prior_close)))

    atr = _wilder(tr, n)
    plus_di = 100 * _wilder(plus_dm, n) / atr
    minus_di = 100 * _wilder(minus_dm, n) / atr
    return plus_di - minus_di


def run(df, buy_th=-20.0, exit_th=0.0, allow_short=True):
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    d = di_diff(high, low, close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if np.isnan(d[i]) or np.isnan(ma200[i]):
            i += 1; continue
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


def grid_search(coin, allow_short):
    df = load_candles_csv(f"data/{coin}_1h_4y.csv")
    buy_ths = [-35.0, -30.0, -25.0, -20.0, -15.0]
    exit_ths = [-5.0, -2.5, 0.0, 2.5, 5.0]
    grid = {}
    for b in buy_ths:
        for e in exit_ths:
            pos = 0
            for start, end in PERIODS:
                mask = (df["time"] >= start) & (df["time"] < end)
                d = df[mask].reset_index(drop=True)
                if len(d) < 500:
                    continue
                r = run(d, buy_th=b, exit_th=e, allow_short=allow_short)
                if r["return"] > 0:
                    pos += 1
            grid[(b, e)] = pos
    return grid, buy_ths, exit_ths


def main():
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    d0 = di_diff(df0["high"].to_numpy(dtype=float), df0["low"].to_numpy(dtype=float),
                 df0["close"].to_numpy(dtype=float))
    d0v = d0[~np.isnan(d0)]
    print(f"[분포확인] BTC DI_diff: 1%={np.percentile(d0v,1):.2f} 5%={np.percentile(d0v,5):.2f} "
          f"95%={np.percentile(d0v,95):.2f} 99%={np.percentile(d0v,99):.2f}\n")

    for coin in COINS:
        for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
            grid, buy_ths, exit_ths = grid_search(coin, allow_short)
            best = max(grid.items(), key=lambda kv: kv[1])
            if best[1] == 4:
                hits = [k for k, v in grid.items() if v == 4]
                print(f"{coin.replace('USDT',''):6} {mode_name}: 4/4 히트 {len(hits)}개 -> {hits}")
            else:
                print(f"{coin.replace('USDT',''):6} {mode_name}: 최고 {best[1]}/4 @ {best[0]}")


if __name__ == "__main__":
    main()
