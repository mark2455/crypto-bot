"""
한국 주식 1시간봉 2년치 수집 (yfinance).
30분봉은 야후가 최근 60일만 줘서 백테스트 불가 → 1시간봉(2년, 4천여개)이 현실적 최선.
data_kr_1h/ 에 저장.

실행:  ~/crypto-bot/venv/bin/python kr_fetch_1h.py
"""
import os
import warnings
import yfinance as yf
import pandas as pd
from kr_coint import STOCKS

warnings.filterwarnings("ignore")
OUT = os.path.join(os.path.dirname(__file__), "data_kr_1h")


def main():
    os.makedirs(OUT, exist_ok=True)
    for code, name in STOCKS.items():
        try:
            df = yf.download(f"{code}.KS", period="730d", interval="60m",
                             progress=False, auto_adjust=True)
            if len(df) == 0:
                print(f"[건너뜀] {name}({code}) 데이터 없음"); continue
            df = df.reset_index()
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            tcol = "Datetime" if "Datetime" in df.columns else "Date"
            out = pd.DataFrame({
                "time": pd.to_datetime(df[tcol]),
                "open": df["Open"], "high": df["High"],
                "low": df["Low"], "close": df["Close"],
            }).dropna()
            out.to_csv(os.path.join(OUT, f"{code}.csv"), index=False)
            print(f"[저장] {name}({code})  {len(out)}개  "
                  f"({out['time'].iloc[0].date()} ~ {out['time'].iloc[-1].date()})")
        except Exception as e:
            print(f"[실패] {name}({code}): {str(e)[:60]}")


if __name__ == "__main__":
    main()
