"""
횡단면 모멘텀 (Cross-Sectional Momentum) — 14개 크립토 코인.

아이디어: 절대적 방향(오를까 내릴까)이 아니라 '상대 순위'만 본다.
  - 매 REBALANCE 봉마다, 최근 LOOKBACK 봉 수익률로 14개 코인 순위
  - 상위 TOP_N 롱 + 하위 BOTTOM_N 숏, 동일가중, 다음 리밸런스까지 유지
  - 페어 트레이딩과 달리 크립토 선물은 개인도 숏이 실제로 가능 → '이론상 알파'가 아님
  - 비교군: 14개 동일가중 buy&hold (그냥 다 사서 들고 있기)

실행:  ~/crypto-bot/venv/bin/python cs_momentum.py
"""
import os
import glob
import numpy as np
import pandas as pd
from candles import load_candles_csv

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

LOOKBACK = 168      # 모멘텀 측정 기간(시간) = 7일
REBALANCE = 24      # 리밸런스 주기(시간) = 1일
TOP_N = 3           # 상위 몇 개 롱
BOTTOM_N = 3        # 하위 몇 개 숏 (0이면 롱온리)
FEE = 0.0004        # 편도 수수료


def load_matrix():
    series = {}
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))):
        name = os.path.basename(path).split("_")[0].replace("USDT", "")
        series[name] = load_candles_csv(path).set_index("time")["close"]
    return pd.DataFrame(series).dropna()


def run(mat, top_n=TOP_N, bottom_n=BOTTOM_N):
    close = mat.to_numpy(dtype=float)
    coins = list(mat.columns)
    n_bars, n_coins = close.shape

    equity = 1.0
    peak = 1.0
    mdd = 0.0
    weights = np.zeros(n_coins)          # 현재 보유 비중(롱+ / 숏-)
    equity_curve = []
    rebalances = 0

    for i in range(LOOKBACK, n_bars):
        # 봉간 가격변화를 현재 비중으로 반영(보유 구간의 손익)
        if i > LOOKBACK:
            ret = close[i] / close[i - 1] - 1
            equity *= 1 + np.dot(weights, ret)
            peak = max(peak, equity)
            mdd = min(mdd, equity / peak - 1)
        equity_curve.append(equity)

        if (i - LOOKBACK) % REBALANCE == 0:
            mom = close[i] / close[i - LOOKBACK] - 1     # 최근 LOOKBACK 수익률
            order = np.argsort(mom)                        # 오름차순
            longs = order[-top_n:] if top_n > 0 else []
            shorts = order[:bottom_n] if bottom_n > 0 else []

            new_w = np.zeros(n_coins)
            if top_n > 0:
                new_w[longs] = 1.0 / top_n
            if bottom_n > 0:
                new_w[shorts] = -1.0 / bottom_n

            turnover = np.abs(new_w - weights).sum()
            equity *= 1 - turnover * FEE                    # 회전 비용
            weights = new_w
            rebalances += 1

    bh = np.mean(close[-1] / close[LOOKBACK] - 1)           # 동일가중 buy&hold
    curve = np.array(equity_curve)
    return {
        "return": equity - 1, "buyhold": bh, "mdd": mdd,
        "rebalances": rebalances, "curve": curve,
    }


def show(tag, r):
    print(f"{tag:16} 리밸런스 {r['rebalances']:>4}회  수익 {r['return']*100:+8.2f}%  "
          f"동일가중보유 {r['buyhold']*100:+8.2f}%  MDD {r['mdd']*100:7.2f}%")


def main():
    mat = load_matrix()
    print(f"[데이터] {len(mat.columns)}개 코인, {len(mat)}개 캔들 "
          f"({mat.index[0].date()} ~ {mat.index[-1].date()})")
    print(f"[설정] lookback {LOOKBACK}h  리밸런스 {REBALANCE}h  롱상위{TOP_N}/숏하위{BOTTOM_N}  "
          f"수수료 {FEE*100:.2f}%\n")

    split = int(len(mat) * 0.7)
    print("=== 롱숏 (상위 롱 + 하위 숏) ===")
    show("전체", run(mat))
    show("train", run(mat.iloc[:split]))
    show("test", run(mat.iloc[split:]))

    print("\n=== 롱온리 (상위만 롱, 숏 없음 — 참고) ===")
    show("전체", run(mat, bottom_n=0))
    show("train", run(mat.iloc[:split], bottom_n=0))
    show("test", run(mat.iloc[split:], bottom_n=0))


if __name__ == "__main__":
    main()
