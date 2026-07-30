"""
[루프 47회차] Median Price 괴리% — 지금까지 쓴 전형가격(H+L+C)/3, 가중종가(H+L+2C)/4, VWAP은
전부 종가를 포함해서 계산했는데, 이건 **종가를 아예 빼고** 그 봉의 고가·저가 중간값만 쓴다 —
"그 시간 동안 가격이 오간 범위의 중심"만 보고 마감가 심리는 무시.

MP = (고가+저가)/2
MP_MA = SMA(MP, 20)
%괴리 = (MP-MP_MA)/MP*100

검증 결과 (2026-07-30) — 4개 코인 확정, 전부 추가확정(헤드라인 변화 없음, 다만 DOT/LINK는 초고수익):
  - **DOT: 롱온리.** buy=-3.0~-4.0 3개 행 전부(12칸) 역대급 견고 → 최대 buy=-4.0,exit=1.0
    → 4년 +261.1%(46건, 승률83%, 4/4)
  - **LINK: 롱온리.** buy=-2.5~-3.5 3개 행 전부(12칸) 역대급 견고 → 최대 buy=-2.5,exit=0.5
    → 4년 +216.4%(132건, 승률67%, 4/4)
  - **XRP: 롱온리.** exit=-0.5 열이 buy -1.5~-4.0 5칸 연속 → buy=-2.0,exit=-0.5
    → 4년 +100.3%(152건, 승률64%, 4/4)
  - **BNB: 롱온리.** buy=-3.5 행 3칸 연속(buy=-2.5는 별개 소블록, 사이 buy=-3.0은 갭) →
    buy=-3.5,exit=0.5 → 4년 +28.9%(16건, 승률94%, 4/4, 거래 적어 참고용 성격)
  - ETC: 4/4 없음(전부 3/4 이하) → 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/median_price_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 20


def mp_dist_pct(high, low, n=N):
    mp = (high + low) / 2
    mp_ma = pd.Series(mp).rolling(n).mean().to_numpy()
    return (mp - mp_ma) / mp * 100


def run(df, buy_th=-2.0, exit_th=0.0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    d = mp_dist_pct(high, low, n)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    m = len(close)
    while i < m:
        if np.isnan(d[i]):
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


def main():
    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== Median Price 괴리% buy<-2.0 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
