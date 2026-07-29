"""
2단계: 캔들(OHLCV) 데이터 받아서 pandas 로 다루기.
- OHLCV = Open(시가) High(고가) Low(저가) Close(종가) Volume(거래량)
- 이동평균선(MA) 두 개를 계산 → 이게 "규칙"의 재료가 된다.

실행:  ~/crypto-bot/venv/bin/python candles.py
"""
import pandas as pd
from config import make_exchange, SYMBOL

TIMEFRAME = "1h"   # 캔들 1개 = 1시간
LIMIT = 200        # 최근 200개
FAST, SLOW = 20, 50  # 단기/장기 이동평균 기간


def fetch_candles(exchange, symbol=SYMBOL, timeframe=TIMEFRAME, limit=LIMIT):
    """캔들 데이터를 받아 pandas DataFrame 으로 반환."""
    raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(raw, columns=["time", "open", "high", "low", "close", "volume"])
    # 밀리초 타임스탬프 → 사람이 읽는 시간(KST)
    df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Seoul")
    return df


def load_candles_csv(path):
    """fetch_history.py 가 저장한 CSV 를 같은 형식의 DataFrame 으로 읽는다."""
    df = pd.read_csv(path, parse_dates=["time"])
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert("Asia/Seoul")
    return df


def add_indicators(df, fast=FAST, slow=SLOW):
    """이동평균선(단기/장기)을 컬럼으로 추가."""
    df[f"ma{fast}"] = df["close"].rolling(fast).mean()
    df[f"ma{slow}"] = df["close"].rolling(slow).mean()
    return df


def main():
    ex = make_exchange()
    df = fetch_candles(ex)
    df = add_indicators(df)

    print(f"[{SYMBOL}] {TIMEFRAME} 캔들 {len(df)}개 수신")
    print(f"기간: {df['time'].iloc[0]}  ~  {df['time'].iloc[-1]}")
    print("\n최근 5개 (시간 / 종가 / 단기MA / 장기MA):")
    view = df[["time", "close", f"ma{FAST}", f"ma{SLOW}"]].tail(5)
    print(view.to_string(index=False))

    # 지금 단기선이 장기선 위인지 아래인지 (추세의 방향)
    last = df.iloc[-1]
    if last[f"ma{FAST}"] > last[f"ma{SLOW}"]:
        print(f"\n현재: 단기MA > 장기MA  → 상승 추세(골든크로스 상태)")
    else:
        print(f"\n현재: 단기MA < 장기MA  → 하락 추세(데드크로스 상태)")


if __name__ == "__main__":
    main()
