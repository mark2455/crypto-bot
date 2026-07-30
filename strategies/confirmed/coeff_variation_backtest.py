"""
[루프 58회차] Coefficient of Variation (CV, 변동계수) z-score —
"가격이 최근 자기 평균 대비 상대적으로 얼마나 흩어져 있는가"를 측정하는 순수 분산도 지표.
Bollinger(%B, 가격의 위치)·ATR/Mass Index/Chaikin Volatility(고가-저가 범위)·Ulcer Index(하락폭 누적)와
전부 다른 메커니즘 — 종가의 롤링 표준편차를 롤링 평균으로 "나눠서" 스케일을 제거한 순수 상대분산.

CV = 롤링표준편차(종가, 48) / 롤링평균(종가, 48) * 100     (48봉 = 2일)
CV_z = (CV - 롤링평균(CV,200)) / 롤링표준편차(CV,200)        (그 코인의 "평소" 변동계수 대비 이례적 수준)

CV_z가 낮음 = 최근 가격이 평소보다 훨씬 조용함(수축/컨솔리데이션) → MA200 추세 방향으로 곧 재개될 가능성.
CV_z가 정상으로 복귀하면(변동성 정상화) 청산. VHF(저변동성 필터)와 유사한 발상이지만 계산식은 완전히 다름
(VHF는 range/합산 기반, CV는 std/mean 기반) — 실제로 상관관계도 낮음.

검증 결과 (2026-07-30, 롱온리 기준):
  - LTC: buy_th=−1.4 고정, exit_th −0.4~+0.2 **4칸 연속 4/4** (한 축 방향 견고 블록, buy_th 인접값
    −1.2/−1.6은 각각 2~3/4로 떨어져 buy축 자체는 좁음 — Force Index DOT 사례와 동일한 "단축 라인" 형태로 인정)
    최적 buy=−1.4 exit=−0.2 → 4년 +107.5%, 거래 64건, 승률 64.1%
    연도별: +2.9% / +43.8% / +32.3% / +5.9% (전부 플러스)
  - 나머지 8코인: 롱온리·롱숏 전부 최고 3/4 이하로 미확정 (ETC 롱숏만 고립셀 1개, 기각)
  - LTC 기존 대표(Volume Profile POC +207.8%)보다 낮아 헤드라인 교체 없음 — 추가 확정 지표로 등재

실행:  PYTHONPATH=. ~/crypto-bot/venv/bin/python strategies/confirmed/coeff_variation_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100
N = 48


def cv_z(close, n=N):
    s = pd.Series(close)
    cv = (s.rolling(n).std() / s.rolling(n).mean()) * 100
    z = (cv - cv.rolling(200).mean()) / cv.rolling(200).std()
    return z.to_numpy()


def run(df, buy_th=-1.4, exit_th=-0.2, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    z = cv_z(close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 250
    n = len(close)
    while i < n:
        if np.isnan(z[i]) or np.isnan(ma200[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (z[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (z[i] > exit_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if z[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and z[i] < buy_th and close[i] < ma200[i]:
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


def grid_search(coin, allow_short):
    df = load_candles_csv(f"data/{coin}_1h_4y.csv")
    buy_ths = [-2.0, -1.8, -1.6, -1.4, -1.2, -1.0]
    exit_ths = [-0.6, -0.4, -0.2, 0.0, 0.2]
    grid = {}
    for b in buy_ths:
        for e in exit_ths:
            pos = 0
            for start, end in PERIODS:
                mask = (df["time"] >= start) & (df["time"] < end)
                d = df[mask].reset_index(drop=True)
                if len(d) < 500:
                    continue
                r = run(d, buy_th=b, exit_th=e, allow_short=allow_short)
                if r["return"] > 0:
                    pos += 1
            grid[(b, e)] = pos
    return grid, buy_ths, exit_ths


def main():
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    z0 = cv_z(df0["close"].to_numpy(dtype=float))
    z0v = z0[~np.isnan(z0)]
    print(f"[분포확인] BTC CV z: 1%={np.percentile(z0v,1):.2f} 5%={np.percentile(z0v,5):.2f} "
          f"95%={np.percentile(z0v,95):.2f} 99%={np.percentile(z0v,99):.2f}\n")

    for coin in COINS:
        for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
            grid, buy_ths, exit_ths = grid_search(coin, allow_short)
            best = max(grid.items(), key=lambda kv: kv[1])
            if best[1] == 4:
                hits = [k for k, v in grid.items() if v == 4]
                print(f"{coin.replace('USDT',''):6} {mode_name}: 4/4 히트 {len(hits)}개 -> {hits}")
            else:
                print(f"{coin.replace('USDT',''):6} {mode_name}: 최고 {best[1]}/4 @ {best[0]}")


if __name__ == "__main__":
    main()
