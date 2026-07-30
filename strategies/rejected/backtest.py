"""
3단계: 백테스팅 — 과거 캔들로 '규칙'을 검증한다.

전략: 이동평균 교차 (MA crossover)
  - 단기MA 가 장기MA 를 위로 뚫으면(골든크로스) → 매수(롱 진입)
  - 단기MA 가 장기MA 를 아래로 뚫으면(데드크로스) → 청산(포지션 종료)
  - 항상 '전액 롱 or 현금' 둘 중 하나인 아주 단순한 버전(레버리지 없음).

핵심: 거래마다 수수료를 빼야 '진짜 성적'이 나온다. 수수료 빼면 대부분의
단순 전략은 시장을 그냥 들고 있는 것(Buy&Hold)보다 못하다 — 그걸 눈으로 확인한다.

실행:  ~/crypto-bot/venv/bin/python backtest.py
"""
import pandas as pd
from config import make_exchange, SYMBOL
from candles import fetch_candles, add_indicators, FAST, SLOW

FEE = 0.0004        # 진입/청산 1회당 수수료 (테이커 0.04% 가정)
TIMEFRAME = "1h"
LIMIT = 1000        # 더 긴 기간으로 검증


def run_backtest(df, fast=FAST, slow=SLOW, fee=FEE):
    """DataFrame(캔들+MA)을 받아 전략을 시뮬레이션하고 결과를 반환."""
    df = df.dropna().reset_index(drop=True)   # MA 가 채워지기 전 구간 제거

    position = 0        # 0=현금, 1=롱
    entry_price = 0.0
    equity = 1.0        # 시작 자본을 1.0(=100%)로 두고 배수로 추적
    trades = []

    for i in range(1, len(df)):
        prev, cur = df.iloc[i - 1], df.iloc[i]
        fast_prev, slow_prev = prev[f"ma{fast}"], prev[f"ma{slow}"]
        fast_cur, slow_cur = cur[f"ma{fast}"], cur[f"ma{slow}"]

        golden = fast_prev <= slow_prev and fast_cur > slow_cur   # 상향 돌파
        dead = fast_prev >= slow_prev and fast_cur < slow_cur     # 하향 돌파
        price = cur["close"]

        if position == 0 and golden:
            position = 1
            entry_price = price
            equity *= (1 - fee)               # 진입 수수료
        elif position == 1 and dead:
            ret = price / entry_price          # 이번 거래 수익률
            equity *= ret * (1 - fee)          # 청산 반영 + 청산 수수료
            trades.append(ret - 1)
            position = 0

    # 마지막에 포지션이 열려있으면 마지막 종가로 청산 처리
    if position == 1:
        ret = df.iloc[-1]["close"] / entry_price
        equity *= ret * (1 - fee)
        trades.append(ret - 1)

    # 비교군: 그냥 처음 사서 끝까지 들고 있기(Buy & Hold)
    buy_hold = df.iloc[-1]["close"] / df.iloc[0]["close"]

    wins = [t for t in trades if t > 0]
    return {
        "strategy_return": equity - 1,       # 전략 총수익률
        "buyhold_return": buy_hold - 1,      # 그냥 들고 있기 수익률
        "num_trades": len(trades),
        "win_rate": (len(wins) / len(trades)) if trades else 0.0,
        "period": (df["time"].iloc[0], df["time"].iloc[-1]),
    }


def main():
    ex = make_exchange()
    df = fetch_candles(ex, timeframe=TIMEFRAME, limit=LIMIT)
    df = add_indicators(df)
    r = run_backtest(df)

    print(f"[백테스팅] {SYMBOL} {TIMEFRAME}  MA{FAST}/{SLOW} 교차 전략")
    print(f"기간: {r['period'][0]}  ~  {r['period'][1]}")
    print(f"거래 횟수     : {r['num_trades']}회")
    print(f"승률          : {r['win_rate']*100:.1f}%")
    print(f"전략 수익률   : {r['strategy_return']*100:+.2f}%   (수수료 {FEE*100:.2f}%/회 반영)")
    print(f"그냥 보유 수익: {r['buyhold_return']*100:+.2f}%   (Buy & Hold)")

    diff = r["strategy_return"] - r["buyhold_return"]
    verdict = "전략이 이김 ✅" if diff > 0 else "그냥 보유가 나음 ❌ (전략 개선 필요)"
    print(f"판정          : {verdict}  (차이 {diff*100:+.2f}%p)")


if __name__ == "__main__":
    main()
