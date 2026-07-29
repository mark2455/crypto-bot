"""
삼각수렴(Triangle Convergence) 돌파 패턴 — 지표가 아닌 '차트 구조' 기반 전략.

원리:
  - 최근 LOOKBACK 봉 안에서 스윙 고점들(저항선 후보)과 스윙 저점들(지지선 후보)을 찾아
    각각 추세선(1차 회귀)을 긋는다.
  - 저항선은 내려오고 지지선은 올라와 '폭(width)'이 창 시작 대비 충분히 좁아지면(수렴) →
    삼각형이 형성됐다고 본다.
  - 그 상태에서 종가가 저항선 위로 뚫으면 롱, 지지선 아래로 뚫으면 숏.
  - 청산: 고정 보유시간(HORIZON) 뒤 또는 반대 신호. lookahead 방지: 피벗은 항상
    'index <= 현재-PIVOT_K' 인 확정된 것만 사용.

실행:  ~/crypto-bot/venv/bin/python triangle_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

PIVOT_K = 5
LOOKBACK = 80
MIN_PIVOTS = 2
CONVERGENCE_RATIO = 0.6   # 창 시작 대비 폭이 이 이하로 좁아져야 '수렴'
HORIZON = 48
MAX_HOLD = 100
FEE = 0.0004


def find_pivots(high, low, k=PIVOT_K):
    hp, lp = [], []
    n = len(high)
    for i in range(k, n - k):
        if high[i] == max(high[i - k:i + k + 1]):
            hp.append(i)
        if low[i] == min(low[i - k:i + k + 1]):
            lp.append(i)
    return hp, lp


def fit_line(xs, ys):
    if len(xs) < 2:
        return None
    return np.polyfit(xs, ys, 1)   # (slope, intercept)


def run(df, allow_short=True):
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    n = len(close)
    hp, lp = find_pivots(high, low)

    trades = []
    n_triangles = 0
    side = 0
    entry = 0.0
    held = 0
    i = LOOKBACK + PIVOT_K + 1
    while i < n:
        if side != 0:
            held += 1
            if held >= HORIZON or held >= MAX_HOLD:
                net = (close[i] / entry - 1 if side == 1 else 1 - close[i] / entry) - 2 * FEE
                trades.append(net)
                side = 0
            i += 1
            continue

        window_start = i - LOOKBACK
        r_hp = [j for j in hp if window_start <= j <= i - PIVOT_K]
        r_lp = [j for j in lp if window_start <= j <= i - PIVOT_K]

        if len(r_hp) >= MIN_PIVOTS and len(r_lp) >= MIN_PIVOTS:
            hp_use, lp_use = r_hp[-3:], r_lp[-3:]
            up = fit_line(hp_use, [high[j] for j in hp_use])
            lo = fit_line(lp_use, [low[j] for j in lp_use])
            if up is not None and lo is not None:
                up_s, up_i = up
                lo_s, lo_i = lo
                upper_now = up_s * i + up_i
                lower_now = lo_s * i + lo_i
                upper_start = up_s * window_start + up_i
                lower_start = lo_s * window_start + lo_i
                width_now = upper_now - lower_now
                width_start = upper_start - lower_start

                if width_start > 0 and 0 < width_now < width_start * CONVERGENCE_RATIO:
                    n_triangles += 1
                    if close[i] > upper_now:
                        side, entry, held = 1, close[i], 0
                    elif allow_short and close[i] < lower_now:
                        side, entry, held = -1, close[i], 0
        i += 1

    if not trades:
        return {"triangles": n_triangles, "trades": 0, "return": 0.0, "win_rate": 0.0}
    t = np.array(trades)
    return {"triangles": n_triangles, "trades": len(t),
            "return": (np.prod(1 + t) - 1) * 100, "win_rate": (t > 0).mean() * 100}


def main():
    COINS = ["DOTUSDT", "LINKUSDT", "ETCUSDT"]
    periods = [
        ("2022-07-30", "2023-07-30", "1년차"),
        ("2023-07-30", "2024-07-30", "2년차"),
        ("2024-07-30", "2025-07-30", "3년차"),
        ("2025-07-30", "2026-07-29", "4년차"),
    ]
    print(f"=== 삼각수렴 돌파 (수렴비율<{CONVERGENCE_RATIO}, 보유 {HORIZON}h, 수수료 {FEE*100:.2f}%×2) ===\n")
    for coin in COINS:
        df = load_candles_csv(f"data/{coin}_1h_4y.csv")
        print(f"[{coin.replace('USDT','')}]")
        for start, end, label in periods:
            mask = (df["time"] >= start) & (df["time"] < end)
            d = df[mask].reset_index(drop=True)
            if len(d) < 300:
                continue
            r = run(d)
            print(f"  {label}  삼각형포착{r['triangles']:>4}  거래{r['trades']:>3}  "
                  f"승률{r['win_rate']:5.1f}%  수익 {r['return']:+7.2f}%")
        r_full = run(df)
        print(f"  ▶ 4년 전체  삼각형포착{r_full['triangles']:>4}  거래{r_full['trades']:>3}  "
              f"승률{r_full['win_rate']:5.1f}%  수익 {r_full['return']:+7.2f}%\n")


if __name__ == "__main__":
    main()
