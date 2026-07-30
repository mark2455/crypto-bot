"""
개선 페어 트레이딩: 공적분(cointegration) 검정 + 동적 헤지비율 (워크포워드).

앞의 pairs_backtest.py 문제: 헤지비율 1 고정, 공적분 검정 없음 → 추세로 벌어진
페어(관계 붕괴)에 계속 물림. 여기서 고친다:

  - 매 REESTIMATE 봉마다, 직전 FORMATION 봉으로:
      · OLS 로 헤지비율 β 추정: logA = α + β·logB
      · Engle-Granger 공적분 검정 → p-value
      · 스프레드 = logA - (α + β·logB), 그 std 로 z-score
  - 공적분일 때만(p < PVAL) 신규 진입 허용 (관계 없으면 쉼)
  - z > Z_ENTRY: A숏 B롱 / z < -Z_ENTRY: A롱 B숏 / |z|<Z_EXIT 익절 / |z|>Z_STOP 손절
  - 모든 통계는 '과거 구간'만 사용(lookahead 없음). 양다리 왕복 수수료 반영. train/test.

실행:  ~/crypto-bot/venv/bin/python pairs_coint_backtest.py
"""
import os
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint
from candles import load_candles_csv

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

FORMATION = 500     # 헤지비율·공적분 추정에 쓰는 직전 구간(시간)
REESTIMATE = 24     # 이 봉마다 β·공적분 재추정(하루)
PVAL = 0.05         # 공적분 인정 p-value 상한
Z_ENTRY = 2.0
Z_EXIT = 0.5
Z_STOP = 3.5
FEE = 0.0004


def load_pair(a, b):
    da = load_candles_csv(os.path.join(DATA_DIR, f"{a}_1h.csv"))[["time", "close"]]
    db = load_candles_csv(os.path.join(DATA_DIR, f"{b}_1h.csv"))[["time", "close"]]
    return da.merge(db, on="time", suffixes=("_a", "_b")).reset_index(drop=True)


def run(m):
    pa = m["close_a"].to_numpy(dtype=float)
    pb = m["close_b"].to_numpy(dtype=float)
    la, lb = np.log(pa), np.log(pb)

    equity = 1.0
    peak = 1.0
    mdd = 0.0
    pos = 0
    ea = eb = beta_pos = 0.0
    trades = []
    stops = 0
    coint_ok_bars = 0

    # 현재 유효한 추정치
    beta = alpha = spread_std = 0.0
    pval = 1.0

    for i in range(FORMATION, len(m)):
        # 주기적으로 β·공적분 재추정 (직전 FORMATION 구간)
        if (i - FORMATION) % REESTIMATE == 0:
            wa, wb = la[i - FORMATION:i], lb[i - FORMATION:i]
            beta, alpha = np.polyfit(wb, wa, 1)          # logA ≈ α + β·logB
            resid = wa - (alpha + beta * wb)
            spread_std = resid.std()
            try:
                pval = coint(wa, wb)[1]                   # Engle-Granger p-value
            except Exception:
                pval = 1.0
        if pval < PVAL:
            coint_ok_bars += 1

        spread = la[i] - (alpha + beta * lb[i])
        z = spread / spread_std if spread_std > 0 else 0.0

        if pos != 0:
            if abs(z) < Z_EXIT or abs(z) > Z_STOP:
                ra = pa[i] / ea - 1
                rb = pb[i] / eb - 1
                # 헤지비율 반영 시장중립: 1단위 A vs β단위 B
                notional = ea + abs(beta_pos) * eb
                pnl = (pa[i] - ea) - beta_pos * (pb[i] - eb)   # 롱스프레드 기준
                gross = (pnl / notional) if pos == 1 else (-pnl / notional)
                net = gross - 4 * FEE
                equity *= 1 + net
                trades.append(net)
                if abs(z) > Z_STOP:
                    stops += 1
                peak = max(peak, equity)
                mdd = min(mdd, equity / peak - 1)
                pos = 0
            continue

        # 신규 진입은 공적분일 때만
        if pval < PVAL:
            if z > Z_ENTRY:
                pos, ea, eb, beta_pos = -1, pa[i], pb[i], beta
            elif z < -Z_ENTRY:
                pos, ea, eb, beta_pos = 1, pa[i], pb[i], beta

    wins = [t for t in trades if t > 0]
    return {
        "trades": len(trades), "stops": stops,
        "coint_pct": coint_ok_bars / max(1, len(m) - FORMATION),
        "win_rate": (len(wins) / len(trades)) if trades else 0.0,
        "return": equity - 1,
        "avg": (sum(trades) / len(trades)) if trades else 0.0,
        "worst": min(trades) if trades else 0.0, "mdd": mdd,
    }


def show(tag, r):
    if r["trades"] == 0:
        print(f"{tag:16} 거래 0   (공적분 구간 {r['coint_pct']*100:.0f}%)"); return
    print(f"{tag:16} 거래 {r['trades']:>4}  손절 {r['stops']:>3}  공적분 {r['coint_pct']*100:3.0f}%  "
          f"승률 {r['win_rate']*100:5.1f}%  수익 {r['return']*100:+7.2f}%  "
          f"평균 {r['avg']*100:+.3f}%  MDD {r['mdd']*100:6.2f}%")


def main():
    print(f"=== 공적분 페어 트레이딩  형성{FORMATION} 재추정{REESTIMATE} p<{PVAL} "
          f"진입z{Z_ENTRY} 손절z{Z_STOP} 수수료{FEE*100:.2f}%×4 ===\n")
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
