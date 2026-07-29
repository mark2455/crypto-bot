"""
한국 주식 페어 트레이딩 백테스트 (공적분 안정 페어 대상, 일봉).

공적분 스크리닝(kr_coint.py)에서 나온 '안정' 페어를 실제로 거래해본다.
- 워크포워드로 β·공적분 재추정, 공적분일 때만 진입, z-score 로 진입/청산/손절.
- 한국 거래비용 반영: 왕복 페어 비용 ≈ 0.4%(매매수수료+매도 거래세 0.18%×2다리).
- 시장중립(롱+숏) 가정으로 '전략의 순수 우위'를 봄.
  ※ 실제 개인은 공매도 제약이 크다 — 이건 '이론적 성능' 측정이다.

실행:  ~/crypto-bot/venv/bin/python kr_pairs_backtest.py
"""
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint
from kr_coint import get_close, STOCKS

FORMATION = 120     # 형성 구간(거래일, ≈반년) — 표본 늘리려 단축
REESTIMATE = 5      # 재추정 주기(주 1회)
PVAL = 0.05
USE_COINT_GATE = False   # 이미 '안정 페어'로 선별했으므로 실시간 공적분 게이트 off
Z_ENTRY, Z_EXIT, Z_STOP = 1.5, 0.5, 3.5   # 진입 임계 낮춰 표본 확보
TCOST = 0.004       # 왕복 페어 거래비용(양다리, 거래세 포함) ≈ 0.4%

STABLE_PAIRS = [
    ("055550", "086790"),   # 신한지주-하나금융
    ("105560", "055550"),   # KB금융-신한지주
    ("005380", "000270"),   # 현대차-기아
]


def run(pa, pb):
    la, lb = np.log(pa), np.log(pb)
    equity = peak = 1.0
    mdd = 0.0
    pos = 0
    ea = eb = beta_pos = 0.0
    trades, stops, coint_ok = [], 0, 0
    beta = alpha = spread_std = 0.0
    pval = 1.0

    for i in range(FORMATION, len(pa)):
        if (i - FORMATION) % REESTIMATE == 0:
            wa, wb = la[i - FORMATION:i], lb[i - FORMATION:i]
            beta, alpha = np.polyfit(wb, wa, 1)
            resid = wa - (alpha + beta * wb)
            spread_std = resid.std()
            try:
                pval = coint(wa, wb, maxlag=1, autolag=None)[1]
            except Exception:
                pval = 1.0
        if pval < PVAL:
            coint_ok += 1
        spread = la[i] - (alpha + beta * lb[i])
        z = spread / spread_std if spread_std > 0 else 0.0

        if pos != 0:
            if abs(z) < Z_EXIT or abs(z) > Z_STOP:
                notional = ea + abs(beta_pos) * eb
                pnl = (pa[i] - ea) - beta_pos * (pb[i] - eb)
                gross = (pnl / notional) if pos == 1 else (-pnl / notional)
                net = gross - TCOST
                equity *= 1 + net
                trades.append(net)
                if abs(z) > Z_STOP:
                    stops += 1
                peak = max(peak, equity)
                mdd = min(mdd, equity / peak - 1)
                pos = 0
            continue

        if (not USE_COINT_GATE) or pval < PVAL:
            if z > Z_ENTRY:
                pos, ea, eb, beta_pos = -1, pa[i], pb[i], beta
            elif z < -Z_ENTRY:
                pos, ea, eb, beta_pos = 1, pa[i], pb[i], beta

    wins = [t for t in trades if t > 0]
    return {
        "trades": len(trades), "stops": stops,
        "coint_pct": coint_ok / max(1, len(pa) - FORMATION),
        "win_rate": (len(wins) / len(trades)) if trades else 0.0,
        "return": equity - 1,
        "worst": min(trades) if trades else 0.0, "mdd": mdd,
    }


def show(tag, r):
    if r["trades"] == 0:
        print(f"{tag:22} 거래 0  (공적분 {r['coint_pct']*100:.0f}%)"); return
    print(f"{tag:22} 거래 {r['trades']:>3}  손절 {r['stops']:>2}  공적분 {r['coint_pct']*100:3.0f}%  "
          f"승률 {r['win_rate']*100:5.1f}%  수익 {r['return']*100:+7.2f}%  MDD {r['mdd']*100:6.2f}%")


def main():
    print(f"=== 한국주식 페어 트레이딩 (형성{FORMATION}일 재추정{REESTIMATE} p<{PVAL} "
          f"진입z{Z_ENTRY} 비용{TCOST*100:.1f}%) ===\n")
    for a, b in STABLE_PAIRS:
        sa, sb = get_close(a), get_close(b)
        m = pd.DataFrame({"a": sa, "b": sb}).dropna()
        pa, pb = m["a"].to_numpy(float), m["b"].to_numpy(float)
        split = int(len(pa) * 0.7)
        name = f"{STOCKS[a]}-{STOCKS[b]}"
        show(f"{name} 전체", run(pa, pb))
        show(f"{name} train", run(pa[:split], pb[:split]))
        show(f"{name} test", run(pa[split:], pb[split:]))
        print("-" * 92)


if __name__ == "__main__":
    main()
