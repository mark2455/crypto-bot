"""
변동성 돌파 전략 (Larry Williams volatility breakout) — 일간 돌파 계열.

아이디어:
  - 오늘 목표가 = 오늘 시가 + K × 전일 변동폭(전일고 - 전일저)
  - 장중 고가가 목표가를 '돌파'하면 그 목표가에 매수(추세가 붙었다고 봄)
  - 당일 종가에 청산 (하루짜리)
  - 돌파 못 하면 그날은 쉼

1시간봉을 일봉으로 리샘플해서 검증. 수수료·train/test·3코인 교차검증.
옵션: 추세필터(전일종가 > MA_TREND 일 때만) 켜고 끄기.

실행:  ~/crypto-bot/venv/bin/python vbreakout_backtest.py
"""
import os
import numpy as np
import pandas as pd
from candles import load_candles_csv

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

K = 0.5          # 돌파 계수 (전일 변동폭의 절반)
FEE = 0.0004     # 매수/매도 1회 수수료 → 왕복 2회
MA_TREND = 5     # 추세필터: 전일 종가 > 최근 MA_TREND일 이동평균일 때만 진입


def to_daily(df):
    """1시간봉 DataFrame 을 일봉 OHLC 로 리샘플."""
    d = df.set_index("time").resample("1D").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()
    return d.reset_index()


def run(daily, use_trend=True):
    o = daily["open"].to_numpy(dtype=float)
    h = daily["high"].to_numpy(dtype=float)
    l = daily["low"].to_numpy(dtype=float)
    c = daily["close"].to_numpy(dtype=float)
    ma = pd.Series(c).rolling(MA_TREND).mean().to_numpy()

    equity = 1.0
    peak = 1.0
    mdd = 0.0
    trades = []

    for i in range(1, len(daily)):
        rng = h[i - 1] - l[i - 1]            # 전일 변동폭
        target = o[i] + K * rng             # 오늘 목표가
        if use_trend and not (c[i - 1] > ma[i - 1]):
            continue
        if h[i] >= target:                  # 장중 목표가 돌파 → 매수 체결
            ret = c[i] / target - 1          # 목표가 매수 → 종가 청산
            net = ret - 2 * FEE              # 왕복 수수료
            equity *= 1 + net
            trades.append(net)
            peak = max(peak, equity)
            mdd = min(mdd, equity / peak - 1)

    wins = [t for t in trades if t > 0]
    bh = c[-1] / c[0] - 1
    return {
        "trades": len(trades),
        "win_rate": (len(wins) / len(trades)) if trades else 0.0,
        "return": equity - 1, "buyhold": bh,
        "avg": (sum(trades) / len(trades)) if trades else 0.0,
        "worst": min(trades) if trades else 0.0, "mdd": mdd,
    }


def show(tag, r):
    if r["trades"] == 0:
        print(f"{tag:18} 거래 0"); return
    print(f"{tag:18} 거래 {r['trades']:>4}  승률 {r['win_rate']*100:5.1f}%  "
          f"수익 {r['return']*100:+8.2f}%  보유 {r['buyhold']*100:+8.2f}%  "
          f"평균 {r['avg']*100:+.3f}%  MDD {r['mdd']*100:6.2f}%")


def main():
    print(f"=== 변동성 돌파 (K={K}, 추세필터 MA{MA_TREND}, 수수료 {FEE*100:.2f}%×왕복) ===\n")
    for coin in COINS:
        d = to_daily(load_candles_csv(os.path.join(DATA_DIR, f"{coin}_1h.csv")))
        split = int(len(d) * 0.7)
        name = coin[:3]
        show(f"{name} 전체", run(d))
        show(f"{name} train", run(d.iloc[:split].reset_index(drop=True)))
        show(f"{name} test", run(d.iloc[split:].reset_index(drop=True)))
        print("-" * 90)

    print("[참고] 추세필터 끈 순수 돌파 (BTC 전체):")
    d = to_daily(load_candles_csv(os.path.join(DATA_DIR, "BTCUSDT_1h.csv")))
    show("BTC 필터OFF", run(d, use_trend=False))


if __name__ == "__main__":
    main()
