"""
Connors RSI (CRSI) — 덜 알려진 RSI 변형 검증.
표준 RSI 하나 대신 세 요소를 합성: RSI(3) + 연속상승/하락 봉 수의 RSI(2) + ROC(100)의 백분위 순위.
CRSI = (RSI(짧은기간) + Streak RSI + ROC 순위) / 3   → 0~100

주장(quantifiedstrategies.com 등): 짧은 lookback + 극단 임계값(10 이하 매수, 50~70 청산)
조합이 표준 RSI(14)/RSI(2) 보다 낫다는 원 출처의 주장을 우리 방식대로 검증.

규칙: CRSI(3,2,100) < 10 매수 → CRSI > 50 청산. 추세필터 없이(원안 그대로) +
      MA200 위에서만(추세필터 버전) 두 가지 다 테스트.

실행:  ~/crypto-bot/venv/bin/python connors_rsi_backtest.py
"""
import os
import glob
import numpy as np
import pandas as pd
from candles import load_candles_csv
from indicator_analysis import rsi, ONE_YEAR

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FEE = 0.0004
MAX_HOLD = 100


def streak(close):
    """연속 상승(+)/하락(-) 봉 수. 방향 안 바뀌면 누적, 바뀌면 1로 리셋."""
    n = len(close)
    s = np.zeros(n)
    for i in range(1, n):
        if close[i] > close[i - 1]:
            s[i] = s[i - 1] + 1 if s[i - 1] > 0 else 1
        elif close[i] < close[i - 1]:
            s[i] = s[i - 1] - 1 if s[i - 1] < 0 else -1
        else:
            s[i] = 0
    return s


def pct_rank(x, period=100):
    """최근 period 개 중 오늘 ROC 가 몇 % 순위인지 (0~100)."""
    return x.rolling(period).apply(lambda w: (w < w.iloc[-1]).sum() / (len(w) - 1) * 100
                                    if len(w) > 1 else 50, raw=False)


def connors_rsi(close, rsi_period=3, streak_period=2, roc_period=100):
    r = rsi(close, rsi_period)
    st = streak(close)
    sr = rsi(st, streak_period)
    roc = pd.Series(close).pct_change() * 100
    pr = pct_rank(roc, roc_period).to_numpy()
    return (r + sr + pr) / 3


def run(df, use_trend_filter=False, buy_th=10, exit_th=50):
    close = df["close"].to_numpy(dtype=float)
    crsi = connors_rsi(close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()

    trades = []
    in_pos = False
    entry = 0.0
    held = 0
    i = 250
    while i < len(close):
        if in_pos:
            held += 1
            if crsi[i] > exit_th or held >= MAX_HOLD:
                trades.append(close[i] / entry - 1 - 2 * FEE)
                in_pos = False
            i += 1
            continue
        trend_ok = (not use_trend_filter) or (close[i] > ma200[i])
        if crsi[i] < buy_th and trend_ok:
            in_pos = True; entry = close[i]; held = 0
        i += 1

    if not trades:
        return {"trades": 0, "return": 0.0, "win_rate": 0.0}
    t = np.array(trades)
    return {"trades": len(t), "return": (np.prod(1 + t) - 1) * 100, "win_rate": (t > 0).mean() * 100}


def show(tag, r):
    print(f"    {tag:14} 거래{r['trades']:>4}  승률{r['win_rate']:5.1f}%  수익{r['return']:+8.2f}%")


def main():
    print(f"=== Connors RSI(3,2,100) <10 매수 / >50 청산  (수수료 {FEE*100:.2f}%×2) ===\n")
    for coin in ["BTCUSDT", "ETHUSDT"]:
        full = load_candles_csv(os.path.join(DATA_DIR, f"{coin}_1h.csv"))
        disc = full.tail(ONE_YEAR).reset_index(drop=True)
        hold = full.head(len(full) - ONE_YEAR).reset_index(drop=True)
        print(f"[{coin.replace('USDT','')}]")
        print("  추세필터 없음(원안)")
        show("발견구간", run(disc, False))
        show("홀드아웃", run(hold, False))
        print("  +추세필터(가격>MA200)")
        show("발견구간", run(disc, True))
        show("홀드아웃", run(hold, True))
        print()

    print("=== 14개 코인 확장 (+추세필터 버전) ===\n")
    both_pos = 0
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))):
        coin = os.path.basename(path).split("_")[0].replace("USDT", "")
        full = load_candles_csv(path)
        disc = full.tail(ONE_YEAR).reset_index(drop=True)
        hold = full.head(len(full) - ONE_YEAR).reset_index(drop=True)
        rd, rh = run(disc, True), run(hold, True)
        flag = "★둘다+" if (rd["return"] > 0 and rh["return"] > 0) else ""
        if flag:
            both_pos += 1
        print(f"  {coin:6} 발견 {rd['return']:+7.2f}%   홀드아웃 {rh['return']:+7.2f}%   {flag}")
    print(f"\n→ 14개 중 {both_pos}개 코인에서 두 기간 다 플러스")


if __name__ == "__main__":
    main()
