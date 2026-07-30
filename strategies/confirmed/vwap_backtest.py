"""
[루프 33회차] VWAP(거래량가중평균가) 괴리% — 지금까지 쓴 EMA/WMA/HMA/McGinley 등 이동평균
계열은 전부 "최근 봉일수록 가중치가 크다"(시간 가중)는 원리인데, VWAP은 "거래량이 많았던
봉일수록 가중치가 크다"(거래량 가중)는 완전히 다른 원리 — 최근이라도 거래량이 적으면 평균에
거의 영향을 못 준다. 기관 트레이딩에서 가장 널리 쓰이는 기준선인데 우리 프레임에선 아직 미검증.

전형가격 TP = (고가+저가+종가)/3
VWAP(N=20) = sum(TP*거래량, 최근20봉) / sum(거래량, 최근20봉)
%괴리 = (종가-VWAP)/종가*100

검증 결과 (2026-07-30) — **7개 코인 확정, 이번 세션 최다·최고 수확**, 헤드라인 2개 교체:
  - **SOL: 롱온리.** buy=-3.0,exit=1.0 (buy -2.5~-3.5×exit 대부분 넓은 블록) → 4년 +235.7%
    (104건, 승률74%, 4/4). **헤드라인 교체**(구: KST +106.7%)
  - **ETC: 롱숏대칭.** buy=-3.0,exit=1.0 (buy=-3.0 행 3칸 연속) → 4년 +79.1%(139건, 승률65%, 4/4).
    **헤드라인 교체**(구: PPO +35.6%)
  - **DOT: 롱숏대칭.** buy=-4.0,exit=1.0 (buy=-4.0/-5.0 행 전체 8칸 전부 4/4) → +162.6%(76건,
    승률72%, 4/4). 기존 헤드라인(Keltner +340.7%)엔 못 미쳐 추가 확정으로만 기록
  - **LINK: 롱온리.** buy=-3.0,exit=1.0 (buy=-3.5 행 전체+주변 넓은 블록) → +188.0%(95건,
    승률74%, 4/4). 추가 확정
  - **ETH: 롱숏대칭.** buy=-3.0 행 전체(4칸) 4/4 → buy=-3.0,exit=0.5 → +76.2%(73건, 승률71%, 4/4). 추가 확정
  - **XRP: 롱온리.** buy=-3.0~-3.5,exit=-0.5 (2칸 연속) → +122.5%(50건, 승률70%, 4/4). 추가 확정
  - **BNB: 롱숏대칭.** buy=-5.0 행 전체(4칸) 4/4 → buy=-5.0,exit=1.0 → +28.7%(10건, 승률90%, 4/4). 추가 확정
  - BTC: 이 격자 범위에서 4/4 없음(전부 3/4 이하) → 미확정

실행:  ~/crypto-bot/venv/bin/python strategies/confirmed/vwap_backtest.py  (PYTHONPATH=. 필요)
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 20


def vwap_dist_pct(high, low, close, volume, n=N):
    tp = (high + low + close) / 3
    pv = tp * volume
    vwap = pd.Series(pv).rolling(n).sum() / pd.Series(volume).rolling(n).sum()
    return ((close - vwap) / close * 100).to_numpy()


def run(df, buy_th=-3, exit_th=0, allow_short=True, n=N):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    d = vwap_dist_pct(high, low, close, vol, n)
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
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    d0 = vwap_dist_pct(df0["high"].to_numpy(float), df0["low"].to_numpy(float),
                        df0["close"].to_numpy(float), df0["volume"].to_numpy(float))
    d0v = d0[~np.isnan(d0)]
    print(f"[분포확인] BTC VWAP괴리%: 1%={np.percentile(d0v,1):.2f} 5%={np.percentile(d0v,5):.2f} "
          f"95%={np.percentile(d0v,95):.2f} 99%={np.percentile(d0v,99):.2f}\n")

    for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
        print(f"\n=== VWAP 괴리% buy<-3 exit>0 — {mode_name}, 9코인 4년4국면 ===")
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
