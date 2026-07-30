"""
[루프 26회차] Ease of Movement (EOM, Richard Arms) — "가격이 거래량 대비 얼마나 쉽게
움직였는가"를 측정. 지금까지 쓴 거래량 지표들과 전부 메커니즘이 다름:
OBV(방향만 누적)·Force Index(가격변화×거래량, 곱셈)·Chaikin(고저범위 기반 자금흐름)·
PVO(거래량 자체 모멘텀, 가격 무관) 어디에도 안 겹침 — EOM은 "거래량 대비 가격의 이동거리"를
나눗셈으로 측정해 "저항 없이 쉽게 움직였는지"를 본다.

distance = 중간값((고가+저가)/2) 의 변화량
1기간EOM = distance * (고가-저가) / 거래량
EOM = SMA(1기간EOM, 14), z-score 정규화(코인간 스케일 보정, 기존 방식과 동일)

극단적으로 낮은(음수) EOM = 가격이 저항 없이 쉽게 밀려내려간 상태 → 되돌림 기대
극단적으로 높은(양수) EOM = 가격이 저항 없이 쉽게 올라간 상태 → 되돌림 기대(숏)

검증 결과 (2026-07-30) — 이번 루프의 최다 확정(3코인), 코인별로 최적 방향이 갈림:
  - **DOT: 롱숏대칭이 롱온리보다 우수.** buy=-1.75,exit=0.5 부근 넓은 연속블록(buy -1.5~-2.0 대부분 4/4)
    → 롱숏 채택, 4년 +279.4%(221건, 4/4). 롱온리는 같은 파라미터로도 4/4지만 +157.0%로 더 낮음
  - **LINK: 롱온리 채택** (롱숏은 3년차 -23%로 3/4 하락). buy=-1.75~-2.5 × exit=0~0.5 넓은 블록
    → buy=-1.75,exit=0.5, 4년 +99.4%(137건, 4/4)
  - **BNB: 롱온리 채택** (롱숏은 2년차 -23%로 3/4 하락). buy=-1.75~-2.5 × exit=-0.5~0.5 넓은 블록
    → buy=-2.5,exit=1.0, 4년 +111.5%(44건, 4/4)
  - **SOL: buy=-1.50,exit=0.5 단 한 칸만 4/4** (양옆 buy=-1.25/-1.75 exit=0.5는 전부 3/4) →
    **고립셀=우연 판정, 미확정**

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/eom_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def eom_z(high, low, volume, smooth=14):
    high = pd.Series(high); low = pd.Series(low); volume = pd.Series(volume)
    mid = (high + low) / 2
    distance = mid.diff()
    rng = high - low
    raw_eom = np.where(volume > 0, distance * rng / volume, 0.0)
    eom = pd.Series(raw_eom).rolling(smooth).mean()
    z = (eom - eom.rolling(200).mean()) / eom.rolling(200).std()
    return z.to_numpy()


def run(df, buy_th=-1.5, exit_th=0.0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    z = eom_z(high, low, vol)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 220
    n = len(close)
    while i < n:
        if np.isnan(z[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (z[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (z[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if z[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and z[i] > sell_th and close[i] < ma200[i]:
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
    z0 = eom_z(df0["high"].to_numpy(float), df0["low"].to_numpy(float), df0["volume"].to_numpy(float))
    z0v = z0[~np.isnan(z0)]
    print(f"[분포확인] BTC EOM z: 1%={np.percentile(z0v,1):.2f} 5%={np.percentile(z0v,5):.2f} "
          f"95%={np.percentile(z0v,95):.2f} 99%={np.percentile(z0v,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== EOM z buy<-1.5 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
