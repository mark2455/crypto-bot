"""
대량 과거 데이터 수집기.
- 바이낸스 '메인넷' 공개 캔들(키 불필요, 공개 시세라 조회만 함)을 페이지네이션으로
  여러 해치 받아 data/ 아래 CSV 로 저장한다.
- 테스트넷은 ~1000개(약 42일)뿐이라 백테스트 표본이 부족 → 여기서 실제 히스토리를 받는다.

실행:  ~/crypto-bot/venv/bin/python fetch_history.py
"""
import os
import time
import ccxt
import pandas as pd

# 공적분 스크리닝용 확대 목록 (관계 있을 법한 코인들)
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT",
    "AVAX/USDT", "DOT/USDT", "LINK/USDT", "LTC/USDT", "BCH/USDT",
    "ETC/USDT", "DOGE/USDT", "ATOM/USDT", "NEAR/USDT",
]
TIMEFRAME = "1h"
YEARS = 2               # 몇 년치를 받을지
BATCH = 1000           # 1회 요청당 캔들 수(공개 엔드포인트 실질 캡)
OUT_DIR = os.path.join(os.path.dirname(__file__), "data")


def make_public_exchange():
    """메인넷 선물 공개 데이터 전용 거래소 (키 없음)."""
    ex = ccxt.binance({
        "enableRateLimit": True,
        "options": {
            "defaultType": "future",
            "fetchMarkets": {"types": ["linear"], "loadAllOptions": False},
        },
    })
    return ex


def fetch_all(ex, symbol, timeframe=TIMEFRAME, years=YEARS):
    tf_ms = ex.parse_timeframe(timeframe) * 1000
    since = ex.milliseconds() - int(years * 365 * 24 * 60 * 60 * 1000)
    now = ex.milliseconds()

    rows = []
    last_ts = None
    while since < now:
        batch = ex.fetch_ohlcv(symbol, timeframe, since=since, limit=BATCH)
        if not batch:
            break
        # 진행이 없으면(같은 마지막 캔들 반복) 종료 — 무한루프 방지
        if last_ts is not None and batch[-1][0] <= last_ts:
            break
        rows += batch
        last_ts = batch[-1][0]
        since = batch[-1][0] + tf_ms
        print(f"  ...{len(rows):>6}개 누적  (마지막: "
              f"{pd.to_datetime(batch[-1][0], unit='ms')})")
        time.sleep(ex.rateLimit / 1000)   # 밴 방지
    return rows


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ex = make_public_exchange()

    for symbol in SYMBOLS:
        print(f"\n[수집] {symbol} {TIMEFRAME}  최근 {YEARS}년치 (메인넷 공개 데이터)")
        try:
            rows = fetch_all(ex, symbol)
            df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume"])
            df = df.drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)
            df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)

            fname = f"{symbol.replace('/', '')}_{TIMEFRAME}.csv"
            path = os.path.join(OUT_DIR, fname)
            df.to_csv(path, index=False)
            print(f"[저장] {path}  ({len(df)}개, "
                  f"{df['time'].iloc[0].date()} ~ {df['time'].iloc[-1].date()})")
        except Exception as e:
            print(f"[건너뜀] {symbol} 수집 실패: {e}")


if __name__ == "__main__":
    main()
