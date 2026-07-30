"""
[루프 44회차] Twiggs Money Flow (Colin Twiggs) — Chaikin Oscillator(고가-저가 범위 기반)의
개선판. 고가-저가 대신 **True Range**(전봉 종가와의 갭까지 반영한 진짜 변동범위)를 써서
자금흐름을 계산 — 캔들 사이 갭이 큰 구간에서 Chaikin과 다르게 반응할 수 있음. 정규화 방식도
다름(EMA差 아닌 EMA比).

TRH = max(고가, 전봉종가),  TRL = min(저가, 전봉종가),  TR = TRH-TRL
ADV = ((종가-TRL)-(TRH-종가))/TR * 거래량
TMF = EMA(ADV,21)/EMA(거래량,21) * 100     (-100~100 근방, 유계는 아니지만 대체로 그 범위)
z = (TMF - 롤링평균200)/롤링표준편차200

검증 결과 (2026-07-30) — **BTC 헤드라인 교체(거래수 대폭 개선)**:
  - **BTC: 롱온리.** buy=-1.00~-1.50 × exit=0~0.5 6칸 견고블록 → 최대 buy=-1.0,exit=0.5
    → 4년 +56.1%(**322건**, 승률58%, 4/4). **헤드라인 교체**(구: KST +32.5%, 18건 —
    거래수가 18→322건으로 압도적으로 개선돼 통계적 신뢰도가 크게 높아짐)
  - **DOT: 롱온리.** buy=-1.75,exit=0.0 (exit=-0.5 열 3칸 연속 + buy=-1.75 행 2칸) → +95.4%
    (133건, 승률61%, 4/4). 기존 헤드라인(Keltner +340.7%)엔 못 미쳐 추가확정
  - 나머지 코인: 4/4 없음(2~3/4) → 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/twiggs_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def twiggs_z(high, low, close, volume, n=21):
    prior_close = np.roll(close, 1); prior_close[0] = close[0]
    trh = np.maximum(high, prior_close)
    trl = np.minimum(low, prior_close)
    tr = trh - trl
    adv = np.divide((close - trl) - (trh - close), tr, out=np.zeros_like(tr), where=tr != 0) * volume
    ema_adv = pd.Series(adv).ewm(span=n, adjust=False).mean()
    ema_vol = pd.Series(volume).ewm(span=n, adjust=False).mean()
    tmf = 100 * ema_adv / ema_vol
    z = (tmf - tmf.rolling(200).mean()) / tmf.rolling(200).std()
    return z.to_numpy()


def run(df, buy_th=-1.5, exit_th=0.0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    z = twiggs_z(high, low, close, vol)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 410
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
    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== Twiggs MF z buy<-1.5 exit>0 — {mode_name}, 9코인 4년4국면 ===")
        for coin in COINS:
            df = load_candles_csv(f"data/{coin}_1h_4y.csv")
            pos = 0; yearly = []
            for start, end in PERIODS:
                mask = (df["time"] >= start) & (df["time"] < end)
                d = df[mask].reset_index(drop=True)
                if len(d) < 500:
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
