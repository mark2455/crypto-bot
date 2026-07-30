"""
공적분 전수 스크리닝: 14개 코인의 모든 페어(91개)를 공적분 검정해서
'진짜 관계있는 페어'를 찾는다.

핵심 = 안정성(stability):
  - 전체/train(앞70%)/test(뒤30%) 각각에서 Engle-Granger 공적분 p-value 계산
  - train 과 test '둘 다' p<0.05 여야 신뢰 (한쪽만이면 우연/불안정)
  - 이렇게 걸러진 페어라야 페어 트레이딩 후보가 된다.

실행:  ~/crypto-bot/venv/bin/python coint_screen.py
"""
import os
import glob
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
PVAL = 0.05


def load_all():
    """모든 코인 종가를 시간 기준으로 정렬한 하나의 표로."""
    series = {}
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))):
        name = os.path.basename(path).split("_")[0].replace("USDT", "")
        df = pd.read_csv(path, parse_dates=["time"])[["time", "close"]]
        series[name] = df.set_index("time")["close"]
    mat = pd.DataFrame(series).dropna()
    return mat


def pval(a, b):
    try:
        return coint(a, b, maxlag=1, autolag=None)[1]
    except Exception:
        return 1.0


def main():
    mat = load_all()
    coins = list(mat.columns)
    log = np.log(mat)
    n = len(log)
    split = int(n * 0.7)
    print(f"[데이터] {len(coins)}개 코인, {n}개 캔들 → 페어 {len(coins)*(len(coins)-1)//2}개 검정\n")

    rows = []
    for i in range(len(coins)):
        for j in range(i + 1, len(coins)):
            a, b = coins[i], coins[j]
            la, lb = log[a].to_numpy(), log[b].to_numpy()
            p_all = pval(la, lb)
            p_tr = pval(la[:split], lb[:split])
            p_te = pval(la[split:], lb[split:])
            stable = p_tr < PVAL and p_te < PVAL
            rows.append((f"{a}-{b}", p_all, p_tr, p_te, stable))

    res = pd.DataFrame(rows, columns=["pair", "p_all", "p_train", "p_test", "stable"])

    print("=== 전체 기간 공적분 상위 12 (p-value 낮을수록 강함) ===")
    top = res.sort_values("p_all").head(12)
    for _, r in top.iterrows():
        flag = "★안정" if r["stable"] else ""
        print(f"  {r['pair']:12} p(전체) {r['p_all']:.3f}  "
              f"p(train) {r['p_train']:.3f}  p(test) {r['p_test']:.3f}  {flag}")

    stable = res[res["stable"]].sort_values("p_all")
    print(f"\n=== ★ train·test 둘 다 공적분(안정) 페어: {len(stable)}개 ===")
    if len(stable) == 0:
        print("  없음 — 2년간 안정적으로 공적분인 페어가 하나도 없음")
    else:
        for _, r in stable.iterrows():
            print(f"  {r['pair']:12} p(train) {r['p_train']:.3f}  p(test) {r['p_test']:.3f}")


if __name__ == "__main__":
    main()
