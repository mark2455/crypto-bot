"""
한국 주식 페어 트레이딩 — 롱온리 버전 (개인 실행 가능, 공매도 없음).

시장중립 롱숏은 개인이 공매도 제약으로 못 함. 그래서:
  - z < -Z_ENTRY (A가 상대적으로 쌈) → A만 롱
  - z > +Z_ENTRY (A가 비쌈 = B가 쌈)   → B만 롱
  - |z| < Z_EXIT 회귀 익절 / |z| > Z_STOP 손절
  - 수익 = 산 종목 하나의 수익률 - 비용(단일다리 왕복 ≈ 0.21%)

★ 약점: 한 종목만 들므로 '시장 방향'에 노출된다(시장중립 아님).
  그래서 그냥 보유(두 종목 평균 buy&hold)와 비교해 '타이밍이 실제로 이득인지' 본다.

실행:  ~/crypto-bot/venv/bin/python kr_pairs_long.py
"""
import numpy as np
import pandas as pd
from kr_coint import get_close, STOCKS
from kr_pairs_backtest import FORMATION, REESTIMATE, Z_ENTRY, Z_EXIT, Z_STOP, STABLE_PAIRS

TCOST = 0.0021      # 단일 종목 왕복(수수료+매도세) ≈ 0.21%


def run(pa, pb):
    la, lb = np.log(pa), np.log(pb)
    equity = peak = 1.0
    mdd = 0.0
    side = 0            # 0=없음, 'A'=A롱, 'B'=B롱
    entry_px = 0.0
    beta = alpha = spread_std = 0.0
    trades = []

    for i in range(FORMATION, len(pa)):
        if (i - FORMATION) % REESTIMATE == 0:
            wa, wb = la[i - FORMATION:i], lb[i - FORMATION:i]
            beta, alpha = np.polyfit(wb, wa, 1)
            spread_std = (wa - (alpha + beta * wb)).std()
        z = (la[i] - (alpha + beta * lb[i])) / spread_std if spread_std > 0 else 0.0

        if side != 0:
            px = pa[i] if side == "A" else pb[i]
            reverted = abs(z) < Z_EXIT
            stop = abs(z) > Z_STOP
            if reverted or stop:
                net = px / entry_px - 1 - TCOST
                equity *= 1 + net
                trades.append(net)
                peak = max(peak, equity)
                mdd = min(mdd, equity / peak - 1)
                side = 0
            continue

        if z < -Z_ENTRY:          # A 저평가 → A 롱
            side, entry_px = "A", pa[i]
        elif z > Z_ENTRY:         # B 저평가 → B 롱
            side, entry_px = "B", pb[i]

    wins = [t for t in trades if t > 0]
    # 비교군: 두 종목 각각 buy&hold 의 평균
    bh = 0.5 * (pa[-1] / pa[FORMATION] - 1) + 0.5 * (pb[-1] / pb[FORMATION] - 1)
    return {
        "trades": len(trades),
        "win_rate": (len(wins) / len(trades)) if trades else 0.0,
        "return": equity - 1, "buyhold": bh,
        "mdd": mdd,
    }


def show(tag, r):
    if r["trades"] == 0:
        print(f"{tag:22} 거래 0"); return
    print(f"{tag:22} 거래 {r['trades']:>3}  승률 {r['win_rate']*100:5.1f}%  "
          f"수익 {r['return']*100:+7.2f}%  보유평균 {r['buyhold']*100:+7.2f}%  MDD {r['mdd']*100:6.2f}%")


def main():
    print(f"=== 한국주식 페어 '롱온리' (형성{FORMATION} 진입z{Z_ENTRY} 비용{TCOST*100:.2f}%) ===")
    print("   (공매도 없음 = 개인 실행 가능. 단 시장방향 노출)\n")
    for a, b in STABLE_PAIRS:
        m = pd.DataFrame({"a": get_close(a), "b": get_close(b)}).dropna()
        pa, pb = m["a"].to_numpy(float), m["b"].to_numpy(float)
        split = int(len(pa) * 0.7)
        name = f"{STOCKS[a]}-{STOCKS[b]}"
        show(f"{name} 전체", run(pa, pb))
        show(f"{name} train", run(pa[:split], pb[:split]))
        show(f"{name} test", run(pa[split:], pb[split:]))
        print("-" * 92)


if __name__ == "__main__":
    main()
