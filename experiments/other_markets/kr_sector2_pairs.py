"""
증권사 / 통신3사 페어 스크리닝 + 백테스트.
은행과 같은 논리: 같은 규제·거시환경을 공유하는 업종이라 공적분 가능성이 높을 것으로 기대.
통신3사는 국내 과점 구조(SKT/KT/LGU+)라 특히 강한 관계가 기대됨.

실행:  ~/crypto-bot/venv/bin/python kr_sector2_pairs.py
"""
import os
import numpy as np
import pandas as pd
from kr_sector_pairs import fetch, pval, PVAL, CACHE
from kr_1h_pairs import run, show

SECTORS = {
    "증권사": {
        "006800": "미래에셋증권", "016360": "삼성증권", "005940": "NH투자증권",
        "039490": "키움증권", "071050": "한국금융지주", "003540": "대신증권",
    },
    "통신3사": {
        "017670": "SK텔레콤", "030200": "KT", "032640": "LG유플러스",
    },
}


def main():
    os.makedirs(CACHE, exist_ok=True)
    for sector, stocks in SECTORS.items():
        print(f"\n{'='*90}\n[섹터] {sector}  ({', '.join(stocks.values())})\n{'='*90}")

        series = {}
        for code, name in stocks.items():
            s = fetch(code)
            if s is None:
                print(f"  [건너뜀] {name}({code}) 데이터 부족/실패")
                continue
            series[code] = s
        if len(series) < 2:
            print("  → 유효 종목 2개 미만, 스킵"); continue

        mat = pd.DataFrame(series).dropna()
        log = np.log(mat)
        codes = list(mat.columns)
        n = len(mat); split = int(n * 0.7)
        print(f"  공통 데이터 {n}개  ({mat.index[0].date()} ~ {mat.index[-1].date()})")

        stable = []
        for i in range(len(codes)):
            for j in range(i + 1, len(codes)):
                a, b = codes[i], codes[j]
                la, lb = log[a].to_numpy(), log[b].to_numpy()
                p_tr = pval(la[:split], lb[:split])
                p_te = pval(la[split:], lb[split:])
                name = f"{stocks[a]}-{stocks[b]}"
                flag = "★안정" if (p_tr < PVAL and p_te < PVAL) else ""
                print(f"  {name:24} p(train) {p_tr:.3f}  p(test) {p_te:.3f}  {flag}")
                if p_tr < PVAL and p_te < PVAL:
                    stable.append((a, b))

        if not stable:
            print(f"  → {sector}: 안정 페어 없음")
            continue

        for a, b in stable:
            m = mat[[a, b]].dropna()
            pa, pb = m[a].to_numpy(float), m[b].to_numpy(float)
            split = int(len(pa) * 0.7)
            name = f"{stocks[a]}-{stocks[b]}"
            print(f"\n  ### {name} 백테스트")
            for mode, label in [("long", "롱온리(실행가능)"), ("ls", "시장중립(참고)")]:
                show(f"    [{label}] 전체", run(pa, pb, mode))
                show(f"    [{label}] train", run(pa[:split], pb[:split], mode))
                show(f"    [{label}] test", run(pa[split:], pb[split:], mode))


if __name__ == "__main__":
    main()
