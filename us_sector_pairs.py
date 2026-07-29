"""
미국 주식 섹터별 페어 트레이딩 (1시간봉, yfinance).

한국과의 결정적 차이: 미국은 마진계좌만 있으면 개인도 공매도가 실제로 가능
→ '시장중립(진짜 알파)'을 이론이 아니라 실행 가능한 전략으로 검증할 수 있다.
데이터도 깨끗함(거래소 접미사 혼선 없음, 유동성 높음, 2년 1시간봉 안정적으로 수신).

섹터별 '진짜 동일사업' 대장주끼리 묶어 공적분 스크리닝 → 안정 페어 백테스트
(시장중립을 이번엔 '참고용'이 아니라 '주력'으로 본다).

실행:  ~/crypto-bot/venv/bin/python us_sector_pairs.py
"""
import os
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from statsmodels.tsa.stattools import coint
from kr_1h_pairs import run, show

warnings.filterwarnings("ignore")
CACHE = os.path.join(os.path.dirname(__file__), "data_us_1h")
PVAL = 0.05

SECTORS = {
    "대형은행": {"JPM": "JPMorgan", "BAC": "BankOfAmerica", "WFC": "WellsFargo",
                "C": "Citigroup", "GS": "GoldmanSachs", "MS": "MorganStanley"},
    "결제네트워크": {"V": "Visa", "MA": "Mastercard"},
    "음료": {"KO": "CocaCola", "PEP": "PepsiCo"},
    "정유메이저": {"XOM": "ExxonMobil", "CVX": "Chevron", "COP": "ConocoPhillips"},
    "홈인테리어유통": {"HD": "HomeDepot", "LOW": "Lowes"},
    "항공사": {"DAL": "Delta", "UAL": "United", "AAL": "American", "LUV": "Southwest"},
    "양자컴퓨팅": {"RGTI": "Rigetti", "IONQ": "IonQ", "QBTS": "D-Wave", "QUBT": "QuantumComputingInc"},
}


def fetch(ticker):
    """미국 주식은 서머타임(EDT/EST)으로 UTC 오프셋이 바뀌어, 문자열로 캐시하면
    재로드 시 파싱이 깨져 시간이 안 맞는다(→ 병합 시 공통행 0개). UTC로 통일해 저장/로드."""
    path = os.path.join(CACHE, f"{ticker}.csv")
    if os.path.exists(path):
        s = pd.read_csv(path, parse_dates=["time"])
        s["time"] = pd.to_datetime(s["time"], utc=True)
        s = s.set_index("time")["close"]
        return s if len(s) > 1000 else None
    df = yf.download(ticker, period="730d", interval="60m", progress=False, auto_adjust=True)
    if len(df) <= 1000:
        return None
    df = df.reset_index()
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    tcol = "Datetime" if "Datetime" in df.columns else "Date"
    s = pd.DataFrame({"time": pd.to_datetime(df[tcol], utc=True), "close": df["Close"]})
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
        for tk, name in stocks.items():
            s = fetch(tk)
            if s is None:
                print(f"  [건너뜀] {name}({tk}) 데이터 부족/실패"); continue
            series[tk] = s
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
                print(f"  {name:28} p(train) {p_tr:.3f}  p(test) {p_te:.3f}  {flag}")
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
            for mode, label in [("ls", "시장중립(주력·실행가능)"), ("long", "롱온리(참고)")]:
                show(f"    [{label}] 전체", run(pa, pb, mode))
                show(f"    [{label}] train", run(pa[:split], pb[:split], mode))
                show(f"    [{label}] test", run(pa[split:], pb[split:], mode))


if __name__ == "__main__":
    main()
