"""
TradingView 인기 전략 2개를 우리 방식(발견구간/홀드아웃, 필요시 14코인 확장)으로 검증.

1) SuperTrend + ADX ("추세강도 매트릭스")
   - SuperTrend(10, 3) 방향이 하락→상승으로 전환 + ADX>25(뚜렷한 추세) → 진입
   - 청산: SuperTrend 가 다시 하락으로 전환할 때
   출처: tradeify.co 2026 인기 지표 조합 가이드

2) "Full Crypto Pack" (MACD+RSI+OBV+EMA) — TradingView 인기 스크립트
   - 양봉(종가>시가) AND 종가>EMA50 AND MACD히스토그램>0 AND RSI<70(과매수아님) AND 거래량>20기간평균
   - 청산: 종가<EMA50 또는 MACD<0 (추세 반전), 최대 보유 100시간
   원래는 4시간봉·BTC/ETH 대상으로 설계됨 — 우리는 1시간봉으로 적용(차이 명시).

실행:  ~/crypto-bot/venv/bin/python tradingview_strategies.py
"""
import os
import glob
import numpy as np
import pandas as pd
from candles import load_candles_csv
from indicator_analysis import rsi, macd, adx, ONE_YEAR

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
FEE = 0.0004
MAX_HOLD = 100


def supertrend(high, low, close, period=10, mult=3):
    h, l, c = pd.Series(high), pd.Series(low), pd.Series(close)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    hl2 = (h + l) / 2
    upper = (hl2 + mult * atr).to_numpy()
    lower = (hl2 - mult * atr).to_numpy()
    n = len(close)
    direction = np.ones(n)     # 1=상승추세, -1=하락추세
    final_upper, final_lower = upper.copy(), lower.copy()
    for i in range(1, n):
        if close[i - 1] > final_upper[i - 1]:
            direction[i] = 1
        elif close[i - 1] < final_lower[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]
            if direction[i] == 1 and lower[i] < final_lower[i - 1]:
                final_lower[i] = final_lower[i - 1]
            if direction[i] == -1 and upper[i] > final_upper[i - 1]:
                final_upper[i] = final_upper[i - 1]
    return direction


def run_supertrend_adx(df):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    st_dir = supertrend(high, low, close)
    adx_v = adx(high, low, close)

    trades = []
    in_pos = False
    entry = 0.0
    i = 50
    while i < len(close):
        if in_pos:
            if st_dir[i] == -1:      # 하락전환 → 청산
                trades.append(close[i] / entry - 1 - 2 * FEE)
                in_pos = False
            i += 1
            continue
        if st_dir[i - 1] == -1 and st_dir[i] == 1 and adx_v[i] > 25:
            in_pos = True
            entry = close[i]
        i += 1

    if not trades:
        return {"trades": 0, "return": 0.0, "win_rate": 0.0}
    t = np.array(trades)
    return {"trades": len(t), "return": (np.prod(1 + t) - 1) * 100, "win_rate": (t > 0).mean() * 100}


def run_cryptopack(df):
    close = df["close"].to_numpy(dtype=float)
    open_ = df["open"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    ema50 = pd.Series(close).ewm(span=50, adjust=False).mean().to_numpy()
    macd_h = macd(close)
    rsi_v = rsi(close)
    vol_ma20 = pd.Series(vol).rolling(20).mean().to_numpy()

    trades = []
    in_pos = False
    entry = 0.0
    held = 0
    i = 200
    while i < len(close):
        if in_pos:
            held += 1
            if close[i] < ema50[i] or macd_h[i] < 0 or held >= MAX_HOLD:
                trades.append(close[i] / entry - 1 - 2 * FEE)
                in_pos = False
            i += 1
            continue
        cond = (close[i] > open_[i]) and (close[i] > ema50[i]) and (macd_h[i] > 0) \
               and (rsi_v[i] < 70) and (vol[i] > vol_ma20[i])
        if cond:
            in_pos = True; entry = close[i]; held = 0
        i += 1

    if not trades:
        return {"trades": 0, "return": 0.0, "win_rate": 0.0}
    t = np.array(trades)
    return {"trades": len(t), "return": (np.prod(1 + t) - 1) * 100, "win_rate": (t > 0).mean() * 100}


def show(tag, r):
    print(f"    {tag:14} 거래{r['trades']:>4}  승률{r['win_rate']:5.1f}%  수익{r['return']:+8.2f}%")


def main():
    print(f"=== TradingView 인기 전략 검증 (수수료 {FEE*100:.2f}%×2) ===\n")
    for coin in ["BTCUSDT", "ETHUSDT"]:
        full = load_candles_csv(os.path.join(DATA_DIR, f"{coin}_1h.csv"))
        disc = full.tail(ONE_YEAR).reset_index(drop=True)
        hold = full.head(len(full) - ONE_YEAR).reset_index(drop=True)
        print(f"[{coin.replace('USDT','')}]")
        print("  1) SuperTrend+ADX>25")
        show("발견구간", run_supertrend_adx(disc))
        show("홀드아웃", run_supertrend_adx(hold))
        print("  2) Full Crypto Pack(MACD+RSI+OBV+EMA)")
        show("발견구간", run_cryptopack(disc))
        show("홀드아웃", run_cryptopack(hold))
        print()


if __name__ == "__main__":
    main()
