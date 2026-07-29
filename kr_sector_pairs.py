"""
섹터별 대장주 페어 트레이딩 (코스닥 중심).

일봉에서 '경제적 근거가 확실한' 은행 페어가 좋은 신호를 보였다가 1시간봉에서
무너진 걸 확인했다(kr_1h_pairs.py). 같은 방식으로, 이번엔 섹터 내부(같은 업종
대장주끼리)로 범위를 좁혀 '진짜 관계있는' 페어를 더 찾아본다.

섹터마다 대장주 3~5개를 묶고:
  1) 섹터 '내부'에서만 페어를 만들어 공적분 스크리닝 (train·test 둘 다 안정)
  2) 안정 페어를 시장중립/롱온리로 백테스트 (kr_1h_pairs.py 의 run() 재사용)

실행:  ~/crypto-bot/venv/bin/python kr_sector_pairs.py
"""
import os
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from statsmodels.tsa.stattools import coint
from kr_1h_pairs import run, show

warnings.filterwarnings("ignore")
CACHE = os.path.join(os.path.dirname(__file__), "data_kr_1h")
PVAL = 0.05

# 섹터별 대장주 (코스닥 중심, 일부는 코스피 이전 종목 포함 — 코드가 자동 판별)
SECTORS = {
    "바이오": {
        "196170": "알테오젠", "028300": "HLB", "141080": "리가켐바이오",
        "298380": "에이비엘바이오", "087010": "펩트론",
    },
    "반도체소부장": {
        "058470": "리노공업", "039030": "이오테크닉스", "240810": "원익IPS",
        "064760": "티씨케이", "036710": "심텍",
    },
    "2차전지소재": {
        "247540": "에코프로비엠", "086520": "에코프로", "066970": "엘앤에프",
    },
    "게임": {
        "263750": "펄어비스", "112040": "위메이드", "078340": "컴투스",
        "194480": "데브시스터즈",
    },
}


def fetch(code):
    """KOSDAQ(.KQ)/KOSPI(.KS) 둘 다 시도해 '더 촘촘한(행이 많은)' 쪽을 채택.
    (한쪽 거래소 코드가 다른 시장의 성긴/엉뚱한 데이터를 반환하는 경우가 있어
    단순 '첫 성공' 방식은 오탐됨 — 반드시 더 큰 쪽으로 비교)"""
    path = os.path.join(CACHE, f"{code}.csv")
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["time"]).set_index("time")["close"]
        return df if len(df) > 1000 else None   # 1시간봉 2년 기준 성긴 데이터 배제

    best = None
    for suffix in (".KQ", ".KS"):
        df = yf.download(f"{code}{suffix}", period="730d", interval="60m",
                         progress=False, auto_adjust=True)
        if len(df) > 100 and (best is None or len(df) > len(best)):
            best = df
    if best is None or len(best) <= 1000:
        return None
    df = best.reset_index()
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    tcol = "Datetime" if "Datetime" in df.columns else "Date"
    s = pd.DataFrame({"time": pd.to_datetime(df[tcol]), "close": df["Close"]})
    s.to_csv(path, index=False)
    return s.set_index("time")["close"]


def pval(a, b):
    try:
        return coint(a, b, maxlag=1, autolag=None)[1]
    except Exception:
        return 1.0


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
            for mode, label in [("ls", "시장중립"), ("long", "롱온리")]:
                show(f"    [{label}] 전체", run(pa, pb, mode))
                show(f"    [{label}] train", run(pa[:split], pb[:split], mode))
                show(f"    [{label}] test", run(pa[split:], pb[split:], mode))


if __name__ == "__main__":
    main()
