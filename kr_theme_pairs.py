"""
2차전지 소재 / 양자암호통신 테마 페어 스크리닝 + 백테스트.

시장중립(숏)은 개인이 실행 못 하므로, 이번엔 '롱온리 실행 가능성'에 무게를 두되
공적분 스크리닝 기준(train·test 둘 다 p<0.05)은 그대로 엄격히 유지한다.
(참고용으로 시장중립 수치도 같이 낸다 — '이론상 알파가 있는지' 비교 목적)

양자암호통신 테마는 실적보다 '테마 동조 매매'로 같이 움직이는 경우가 많아
색다른 공적분 패턴이 나올 수 있는지 확인한다.

실행:  ~/crypto-bot/venv/bin/python kr_theme_pairs.py
"""
import os
import numpy as np
import pandas as pd
from kr_sector_pairs import fetch, pval, PVAL, CACHE
from kr_1h_pairs import run, show

SECTORS = {
    "양자암호통신테마": {
        "046970": "우리로", "056360": "코위버", "115440": "우리넷",
        "214430": "엑스게이트", "065440": "이루온",
        "032820": "우리기술", "076610": "텔레필드",
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
                print(f"  {name:22} p(train) {p_tr:.3f}  p(test) {p_te:.3f}  {flag}")
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
