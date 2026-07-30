"""
차트 패턴 3종 + 조합 검증: 삼각수렴 / 이중바닥·이중천장 / 깃발형(플래그)

1) 삼각수렴(triangle_backtest.py 재사용) — 이미 검증, 여기선 신호 함수만 재정의
2) 이중바닥(더블바텀, 반전): 비슷한 높이의 저점 2개 + 그 사이 고점(넥라인) 돌파 → 롱
   이중천장(더블탑, 반전): 비슷한 높이의 고점 2개 + 그 사이 저점(넥라인) 돌파 → 숏
3) 깃발형(플래그, 추세지속): 강한 임펄스(급등/급락) 후 좁은 횡보, 그 횡보 범위를 임펄스
   방향으로 재돌파 → 그 방향 진입

조합: 세 패턴 중 '어느 하나라도' 신호를 내면 진입 (앙상블).
lookahead 방지: 피벗은 항상 index<=현재-PIVOT_K 인 확정된 것만 사용.

실행:  ~/crypto-bot/venv/bin/python chart_patterns.py
"""
import numpy as np
from candles import load_candles_csv

PIVOT_K = 5
LOOKBACK = 80
FEE = 0.0004
HORIZON = 48
MAX_HOLD = 100

# 더블탑/바텀 설정
DB_TOLERANCE = 0.02      # 두 저점/고점이 이 비율 이내로 비슷해야 함
# 플래그 설정
IMPULSE_WIN = 20
IMPULSE_TH = 0.08        # 임펄스 최소 등락률
FLAG_WIN = 10
FLAG_TIGHT = 0.03        # 횡보 구간 폭/가격 비율 최대


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
    return np.polyfit(xs, ys, 1)


def signal_triangle(i, high, low, close, hp, lp, ratio=0.6):
    window_start = i - LOOKBACK
    r_hp = [j for j in hp if window_start <= j <= i - PIVOT_K]
    r_lp = [j for j in lp if window_start <= j <= i - PIVOT_K]
    if len(r_hp) < 2 or len(r_lp) < 2:
        return 0
    hp_use, lp_use = r_hp[-3:], r_lp[-3:]
    up = fit_line(hp_use, [high[j] for j in hp_use])
    lo = fit_line(lp_use, [low[j] for j in lp_use])
    if up is None or lo is None:
        return 0
    up_s, up_i = up; lo_s, lo_i = lo
    upper_now = up_s * i + up_i
    lower_now = lo_s * i + lo_i
    upper_start = up_s * window_start + up_i
    lower_start = lo_s * window_start + lo_i
    width_now = upper_now - lower_now
    width_start = upper_start - lower_start
    if width_start > 0 and 0 < width_now < width_start * ratio:
        if close[i] > upper_now:
            return 1
        if close[i] < lower_now:
            return -1
    return 0


def signal_double(i, high, low, close, hp, lp):
    window_start = i - LOOKBACK
    r_lp = [j for j in lp if window_start <= j <= i - PIVOT_K]
    if len(r_lp) >= 2:
        l1, l2 = r_lp[-2], r_lp[-1]
        if abs(low[l1] - low[l2]) / low[l1] < DB_TOLERANCE:
            between = [j for j in hp if l1 < j < l2]
            if between:
                neckline = max(high[j] for j in between)
                if close[i] > neckline:
                    return 1
    r_hp = [j for j in hp if window_start <= j <= i - PIVOT_K]
    if len(r_hp) >= 2:
        h1, h2 = r_hp[-2], r_hp[-1]
        if abs(high[h1] - high[h2]) / high[h1] < DB_TOLERANCE:
            between = [j for j in lp if h1 < j < h2]
            if between:
                neckline = min(low[j] for j in between)
                if close[i] < neckline:
                    return -1
    return 0


def signal_flag(i, high, low, close):
    if i < IMPULSE_WIN + FLAG_WIN:
        return 0
    impulse_start = i - FLAG_WIN - IMPULSE_WIN
    impulse_end = i - FLAG_WIN
    imp_ret = close[impulse_end] / close[impulse_start] - 1
    flag_high = high[impulse_end:i].max()
    flag_low = low[impulse_end:i].min()
    mid = close[impulse_end]
    tight = (flag_high - flag_low) / mid < FLAG_TIGHT
    if not tight:
        return 0
    if imp_ret > IMPULSE_TH and close[i] > flag_high:
        return 1
    if imp_ret < -IMPULSE_TH and close[i] < flag_low:
        return -1
    return 0


def run(df, mode="combo"):
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    n = len(close)
    hp, lp = find_pivots(high, low)

    trades = []
    side = 0; entry = 0.0; held = 0
    i = LOOKBACK + PIVOT_K + 1
    while i < n:
        if side != 0:
            held += 1
            if held >= HORIZON or held >= MAX_HOLD:
                net = (close[i] / entry - 1 if side == 1 else 1 - close[i] / entry) - 2 * FEE
                trades.append(net)
                side = 0
            i += 1; continue

        sig = 0
        s_tri = signal_triangle(i, high, low, close, hp, lp)
        s_db = signal_double(i, high, low, close, hp, lp)
        s_flag = signal_flag(i, high, low, close)

        if mode == "triangle":
            sig = s_tri
        elif mode == "double":
            sig = s_db
        elif mode == "flag":
            sig = s_flag
        elif mode == "combo":
            votes = [s for s in (s_tri, s_db, s_flag) if s != 0]
            if votes:
                sig = votes[0]   # 먼저 발생한 신호 채택(동시면 삼각→더블→플래그 순)

        if sig == 1:
            side, entry, held = 1, close[i], 0
        elif sig == -1:
            side, entry, held = -1, close[i], 0
        i += 1

    if not trades:
        return {"trades": 0, "return": 0.0, "win_rate": 0.0}
    t = np.array(trades)
    return {"trades": len(t), "return": (np.prod(1 + t) - 1) * 100, "win_rate": (t > 0).mean() * 100}


def main():
    COINS = ["DOTUSDT", "LINKUSDT", "ETCUSDT"]
    periods = [
        ("2022-07-30", "2023-07-30", "1년차"),
        ("2023-07-30", "2024-07-30", "2년차"),
        ("2024-07-30", "2025-07-30", "3년차"),
        ("2025-07-30", "2026-07-29", "4년차"),
    ]
    for coin in COINS:
        df = load_candles_csv(f"data/{coin}_1h_4y.csv")
        print(f"\n{'='*80}\n[{coin.replace('USDT','')}]\n{'='*80}")
        for mode, label in [("triangle", "삼각수렴"), ("double", "이중바닥/천장"),
                             ("flag", "깃발형"), ("combo", "조합(앙상블)")]:
            print(f"  --- {label} ---")
            for start, end, plabel in periods:
                mask = (df["time"] >= start) & (df["time"] < end)
                d = df[mask].reset_index(drop=True)
                if len(d) < 300:
                    continue
                r = run(d, mode)
                print(f"    {plabel}  거래{r['trades']:>3}  승률{r['win_rate']:5.1f}%  수익 {r['return']:+7.2f}%")
            r_full = run(df, mode)
            print(f"    ▶4년전체  거래{r_full['trades']:>3}  승률{r_full['win_rate']:5.1f}%  수익 {r_full['return']:+7.2f}%")


if __name__ == "__main__":
    main()
