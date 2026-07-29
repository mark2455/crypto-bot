"""
한국 주식(코스피) 섹터 페어 공적분 스크리닝.
크립토와 달리 같은 섹터 종목은 진짜 경제적 관계가 있어 안정적 공적분 가능성이 높다.
이걸 데이터로 확인한다 — 크립토(91개 중 1개 안정)보다 나은지.

- FinanceDataReader 로 일봉 종가 수집(무료), data_kr/ 캐시.
- 전체/train/test 각각 Engle-Granger 공적분 → train·test 둘 다 p<0.05 면 '안정'.

실행:  ~/crypto-bot/venv/bin/python kr_coint.py
"""
import os
import numpy as np
import pandas as pd
import FinanceDataReader as fdr
from statsmodels.tsa.stattools import coint

CACHE = os.path.join(os.path.dirname(__file__), "data_kr")
START, END = "2021-01-01", "2026-07-28"
PVAL = 0.05

# 같은 섹터끼리 묶은 종목 (섹터 내 페어가 공적분일 가능성 높음)
STOCKS = {
    "005930": "삼성전자", "000660": "SK하이닉스",          # 반도체
    "005380": "현대차",   "000270": "기아",                # 자동차
    "105560": "KB금융",   "055550": "신한지주",
    "086790": "하나금융", "316140": "우리금융",            # 은행
    "035420": "NAVER",    "035720": "카카오",              # 인터넷
    "051910": "LG화학",   "006400": "삼성SDI",             # 2차전지/화학
    "005490": "POSCO홀딩스", "004020": "현대제철",         # 철강
    "207940": "삼성바이오", "068270": "셀트리온",          # 바이오
}


def get_close(code):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{code}.csv")
    if os.path.exists(path):
        s = pd.read_csv(path, parse_dates=["Date"]).set_index("Date")["Close"]
    else:
        df = fdr.DataReader(code, START, END)
        s = df["Close"]
        s.to_frame().to_csv(path)
    s.name = code
    return s


def pval(a, b):
    try:
        return coint(a, b, maxlag=1, autolag=None)[1]
    except Exception:
        return 1.0


def main():
    print(f"[수집] {len(STOCKS)}개 종목 일봉 ({START}~{END})")
    cols = {}
    for code in STOCKS:
        cols[code] = get_close(code)
    mat = pd.DataFrame(cols).dropna()
    log = np.log(mat)
    n = len(log); split = int(n * 0.7)
    codes = list(mat.columns)
    print(f"[정렬] 공통 거래일 {n}일 → 페어 {len(codes)*(len(codes)-1)//2}개 검정\n")

    rows = []
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            a, b = codes[i], codes[j]
            la, lb = log[a].to_numpy(), log[b].to_numpy()
            p_all = pval(la, lb)
            p_tr = pval(la[:split], lb[:split])
            p_te = pval(la[split:], lb[split:])
            name = f"{STOCKS[a]}-{STOCKS[b]}"
            rows.append((name, p_all, p_tr, p_te, p_tr < PVAL and p_te < PVAL))

    res = pd.DataFrame(rows, columns=["pair", "p_all", "p_train", "p_test", "stable"])

    print("=== 전체 공적분 상위 12 ===")
    for _, r in res.sort_values("p_all").head(12).iterrows():
        flag = "★안정" if r["stable"] else ""
        print(f"  {r['pair']:20} p(전체) {r['p_all']:.3f}  "
              f"train {r['p_train']:.3f}  test {r['p_test']:.3f}  {flag}")

    stable = res[res["stable"]].sort_values("p_all")
    print(f"\n=== ★ train·test 둘 다 공적분(안정): {len(stable)}개 / {len(res)}개 ===")
    for _, r in stable.iterrows():
        print(f"  {r['pair']:20} train {r['p_train']:.3f}  test {r['p_test']:.3f}")


if __name__ == "__main__":
    main()
