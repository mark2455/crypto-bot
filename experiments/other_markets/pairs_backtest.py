"""
페어 트레이딩 / 통계적 차익거래 (시장 중립).

아이디어(방향성 예측 없음):
  - 두 관련 코인의 스프레드 = log(A) - log(B)  (상대 가격)
  - 스프레드의 롤링 z-score 로 '평소보다 얼마나 벌어졌나'를 측정
  - z > +Z_ENTRY  : 스프레드 과대 → A 숏 + B 롱  (스프레드 축소에 베팅)
  - z < -Z_ENTRY  : 스프레드 과소 → A 롱 + B 숏
  - |z| < Z_EXIT  : 평균 회귀 완료 → 청산(익절)
  - |z| > Z_STOP  : 관계가 깨짐 → 손절
  - 시장 전체가 오르든 내리든 상관없음(두 다리가 상쇄) = market-neutral.

정직성 장치: 롤링 통계(과거만 사용), 양다리 왕복 수수료(4회), train/test 분리, 3개 페어 교차검증.
단순화: 헤지비율 = 1 (로그 스프레드). 실무는 롤링 OLS 로 beta 추정하지만 여기선 1로 둠.

실행:  ~/crypto-bot/venv/bin/python pairs_backtest.py
"""
import os
import numpy as np
import pandas as pd
from candles import load_candles_csv

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

WINDOW = 100        # z-score 롤링 창(시간)
Z_ENTRY = 2.0       # 이만큼 벌어지면 진입
Z_EXIT = 0.5        # 이 안으로 좁혀지면 청산(익절)
Z_STOP = 3.5        # 이보다 더 벌어지면 손절(관계 붕괴)
FEE = 0.0004        # 한 다리 1회 수수료 → 왕복 양다리 = 4회


def load_pair(a, b):
    """두 코인 CSV 를 시간 기준으로 정렬해 종가 배열 반환."""
    da = load_candles_csv(os.path.join(DATA_DIR, f"{a}_1h.csv"))[["time", "close"]]
    db = load_candles_csv(os.path.join(DATA_DIR, f"{b}_1h.csv"))[["time", "close"]]
    m = da.merge(db, on="time", suffixes=("_a", "_b")).reset_index(drop=True)
    return m


def run(m):
    pa = m["close_a"].to_numpy(dtype=float)
    pb = m["close_b"].to_numpy(dtype=float)
    spread = np.log(pa) - np.log(pb)
    s = pd.Series(spread)
    mean = s.rolling(WINDOW).mean().to_numpy()
    std = s.rolling(WINDOW).std().to_numpy()
    z = (spread - mean) / std

    equity = 1.0
    peak = 1.0
    mdd = 0.0
    pos = 0            # 0=없음, +1=롱스프레드(A롱B숏), -1=숏스프레드(A숏B롱)
    ea = eb = 0.0      # 진입 시 A, B 가격
    trades = []
    stops = 0

    for i in range(WINDOW, len(m)):
        if np.isnan(z[i]):
            continue
        if pos != 0:
            hit_exit = abs(z[i]) < Z_EXIT
            hit_stop = abs(z[i]) > Z_STOP
            if hit_exit or hit_stop:
                ra = pa[i] / ea - 1        # A 다리 수익률
                rb = pb[i] / eb - 1        # B 다리 수익률
                # 롱스프레드=A롱B숏 → ra - rb / 숏스프레드 → rb - ra
                gross = (ra - rb) if pos == 1 else (rb - ra)
                net = gross - 4 * FEE       # 양다리 왕복 수수료
                equity *= 1 + net
                trades.append(net)
                if hit_stop:
                    stops += 1
                peak = max(peak, equity)
                mdd = min(mdd, equity / peak - 1)
                pos = 0
            continue

        if z[i] > Z_ENTRY:
            pos, ea, eb = -1, pa[i], pb[i]     # 스프레드 과대 → A숏 B롱
        elif z[i] < -Z_ENTRY:
            pos, ea, eb = 1, pa[i], pb[i]      # 스프레드 과소 → A롱 B숏

    wins = [t for t in trades if t > 0]
    return {
        "trades": len(trades), "stops": stops,
        "win_rate": (len(wins) / len(trades)) if trades else 0.0,
        "return": equity - 1,
        "avg": (sum(trades) / len(trades)) if trades else 0.0,
        "worst": min(trades) if trades else 0.0,
        "best": max(trades) if trades else 0.0,
        "mdd": mdd,
    }


def show(tag, r):
    if r["trades"] == 0:
        print(f"{tag:16} 거래 0"); return
    print(f"{tag:16} 거래 {r['trades']:>4}  손절 {r['stops']:>3}  승률 {r['win_rate']*100:5.1f}%  "
          f"수익 {r['return']*100:+7.2f}%  평균 {r['avg']*100:+.3f}%  "
          f"최악 {r['worst']*100:+6.2f}%  MDD {r['mdd']*100:6.2f}%")


def main():
    print(f"=== 페어 트레이딩 (시장중립)  창{WINDOW} 진입z{Z_ENTRY} 청산z{Z_EXIT} 손절z{Z_STOP} "
          f"수수료 {FEE*100:.2f}%×4 ===\n")
    pairs = [("BTCUSDT", "ETHUSDT"), ("BTCUSDT", "SOLUSDT"), ("ETHUSDT", "SOLUSDT")]
    for a, b in pairs:
        m = load_pair(a, b)
        name = f"{a[:3]}-{b[:3]}"
        split = int(len(m) * 0.7)
        show(f"{name} 전체", run(m))
        show(f"{name} train", run(m.iloc[:split].reset_index(drop=True)))
        show(f"{name} test", run(m.iloc[split:].reset_index(drop=True)))
        print("-" * 96)


if __name__ == "__main__":
    main()
