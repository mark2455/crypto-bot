"""
한국 주식 1시간봉 페어 트레이딩 (공적분 스크리닝 + 시장중립/롱온리 백테스트).

일봉보다 7배 촘촘 → 거래 표본이 많아져 검증이 견고해진다.
1) 16종목 1시간봉으로 공적분 전수 스크리닝 → train·test 둘 다 공적분인 '안정' 페어
2) 안정 페어를 두 방식으로 백테스트:
   - 시장중립(롱+숏): 진짜 알파. 단 개인 공매도 제약 → '이론 성능'
   - 롱온리(싼쪽만 롱): 개인 실행 가능. 단 시장방향 노출
   각각 train/test + '그냥 보유' 비교.

실행:  ~/crypto-bot/venv/bin/python kr_1h_pairs.py
"""
import os
import glob
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint
from kr_coint import STOCKS

DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data_kr_1h")
FORMATION = 500     # 형성 구간(시간, ≈70 거래일)
REESTIMATE = 35     # 재추정 주기(≈주 1회)
PVAL = 0.05
Z_ENTRY, Z_EXIT, Z_STOP = 2.0, 0.5, 3.5
COST_LS = 0.004     # 시장중립 왕복 페어 비용(양다리+거래세)
COST_LONG = 0.0021  # 롱온리 단일종목 왕복


def load_all():
    series = {}
    for path in sorted(glob.glob(os.path.join(DATA, "*.csv"))):
        code = os.path.basename(path).replace(".csv", "")
        df = pd.read_csv(path, parse_dates=["time"])
        series[code] = df.set_index("time")["close"]
    return pd.DataFrame(series).dropna()


def pval(a, b):
    try:
        return coint(a, b, maxlag=1, autolag=None)[1]
    except Exception:
        return 1.0


def screen(log):
    n = len(log); split = int(n * 0.7)
    codes = list(log.columns)
    stable = []
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            a, b = codes[i], codes[j]
            la, lb = log[a].to_numpy(), log[b].to_numpy()
            if pval(la[:split], lb[:split]) < PVAL and pval(la[split:], lb[split:]) < PVAL:
                stable.append((a, b))
    return stable


def run(pa, pb, mode):
    la, lb = np.log(pa), np.log(pb)
    equity = peak = 1.0
    mdd = 0.0
    pos = 0            # 0/ +1=롱스프레드 / -1=숏스프레드   (long모드: 'A'/'B')
    ea = eb = beta_pos = 0.0
    beta = alpha = sd = 0.0
    trades = []
    for i in range(FORMATION, len(pa)):
        if (i - FORMATION) % REESTIMATE == 0:
            wa, wb = la[i - FORMATION:i], lb[i - FORMATION:i]
            beta, alpha = np.polyfit(wb, wa, 1)
            sd = (wa - (alpha + beta * wb)).std()
        z = (la[i] - (alpha + beta * lb[i])) / sd if sd > 0 else 0.0

        if pos != 0:
            if abs(z) < Z_EXIT or abs(z) > Z_STOP:
                if mode == "ls":
                    notional = ea + abs(beta_pos) * eb
                    pnl = (pa[i] - ea) - beta_pos * (pb[i] - eb)
                    gross = (pnl / notional) if pos == 1 else (-pnl / notional)
                    net = gross - COST_LS
                else:  # long-only
                    px = pa[i] if pos == "A" else pb[i]
                    net = px / ea - 1 - COST_LONG
                equity *= 1 + net
                trades.append(net)
                peak = max(peak, equity); mdd = min(mdd, equity / peak - 1)
                pos = 0
            continue

        if z < -Z_ENTRY:
            pos = 1 if mode == "ls" else "A"
            ea, eb, beta_pos = pa[i], pb[i], beta
        elif z > Z_ENTRY:
            pos = -1 if mode == "ls" else "B"
            ea, eb, beta_pos = (pa[i] if mode == "ls" else pb[i]), pb[i], beta

    wins = [t for t in trades if t > 0]
    bh = 0.5 * (pa[-1] / pa[FORMATION] - 1) + 0.5 * (pb[-1] / pb[FORMATION] - 1)
    return {"trades": len(trades), "win": (len(wins) / len(trades)) if trades else 0,
            "ret": equity - 1, "bh": bh, "mdd": mdd}


def show(tag, r):
    if r["trades"] == 0:
        print(f"{tag:28} 거래 0"); return
    print(f"{tag:28} 거래 {r['trades']:>3}  승률 {r['win']*100:5.1f}%  "
          f"수익 {r['ret']*100:+7.2f}%  보유 {r['bh']*100:+7.2f}%  MDD {r['mdd']*100:6.2f}%")


def main():
    mat = load_all()
    log = np.log(mat)
    print(f"[데이터] 16종목 1시간봉 {len(mat)}개  공통기간 {mat.index[0].date()}~{mat.index[-1].date()}")
    stable = screen(log)
    print(f"[스크리닝] train·test 둘 다 공적분(안정) 페어: "
          f"{', '.join(f'{STOCKS[a]}-{STOCKS[b]}' for a, b in stable) or '없음'}\n")

    for a, b in stable:
        m = mat[[a, b]].dropna()
        pa, pb = m[a].to_numpy(float), m[b].to_numpy(float)
        split = int(len(pa) * 0.7)
        name = f"{STOCKS[a]}-{STOCKS[b]}"
        print(f"### {name}")
        for mode, label in [("ls", "시장중립"), ("long", "롱온리")]:
            show(f"  [{label}] 전체", run(pa, pb, mode))
            show(f"  [{label}] train", run(pa[:split], pb[:split], mode))
            show(f"  [{label}] test", run(pa[split:], pb[split:], mode))
        print("-" * 84)


if __name__ == "__main__":
    main()
