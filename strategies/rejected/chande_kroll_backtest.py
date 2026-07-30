"""
[루프 37회차] Chande Kroll Stop (Tushar Chande) — ATR과 극값(최고/최저가)을 2단계로 결합한
트레일링 스탑 채널. Donchian(순수 극값)이나 Keltner(EMA중심+ATR)와 둘 다 다른 방식:
1단계로 "최근 극값에서 ATR만큼 뺀/더한" 후보선을 만들고, 2단계로 그 후보선들의 롤링 극값을
다시 취해 완성한다 — 극값과 변동성을 두 번 겹쳐 거른다는 점이 독특함.

ATR(10)
1단계: high_raw = rolling_max(고가,10) - x*ATR,  low_raw = rolling_min(저가,10) + x*ATR  (x=1)
2단계: LongStop  = rolling_max(high_raw, 9)   (지지선, 항상 종가 아래쪽에 위치하도록 설계)
        ShortStop = rolling_min(low_raw, 9)    (저항선)
%Position = (종가-LongStop)/(ShortStop-LongStop)   0=지지선 근접, 1=저항선 근접

실행:  ~/crypto-bot/venv/bin/python chande_kroll_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def atr(high, low, close, n=10):
    prior_close = np.roll(close, 1); prior_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prior_close), np.abs(low - prior_close)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def chande_kroll_pct(high, low, close, p=10, q=9, x=1.0):
    a = atr(high, low, close, p)
    high_raw = pd.Series(high).rolling(p).max().to_numpy() - x * a
    low_raw = pd.Series(low).rolling(p).min().to_numpy() + x * a
    long_stop = pd.Series(high_raw).rolling(q).max().to_numpy()
    short_stop = pd.Series(low_raw).rolling(q).min().to_numpy()
    rng = short_stop - long_stop
    return np.divide(close - long_stop, rng, out=np.full_like(rng, 0.5), where=rng != 0)


def run(df, buy_th=0.1, exit_th=0.5, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    p = chande_kroll_pct(high, low, close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = 1 - buy_th, 1 - exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 230
    n = len(close)
    while i < n:
        if np.isnan(p[i]):
            i += 1; continue
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
    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== Chande Kroll %Pos buy<0.1 exit>0.5 — {mode_name}, 9코인 4년4국면 ===")
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
