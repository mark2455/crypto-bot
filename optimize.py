"""
B단계: 최적 MA 조합 탐색 (+ 과최적화 검증).

두 가지를 한다:
  1) 여러 (단기, 장기) MA 조합을 전부 돌려 성적표를 만든다.
  2) '과최적화' 함정 확인 — 데이터를 앞(train)/뒤(test)로 나눠서,
     train 에서 1등이던 조합이 test(처음 보는 기간)에서도 통하는지 본다.
     보통 안 통한다. 이게 봇 개발에서 제일 중요한 교훈이다.

실행:  ~/crypto-bot/venv/bin/python optimize.py
"""
import pandas as pd
from config import make_exchange, SYMBOL
from candles import fetch_candles
from backtest import run_backtest, FEE

TIMEFRAME = "1h"
LIMIT = 1500                      # 바이낸스 선물 klines 1회 최대치
FASTS = [5, 10, 15, 20, 25, 30]   # 단기 후보
SLOWS = [40, 50, 60, 80, 100, 120]  # 장기 후보


def sweep(df):
    """모든 (fast, slow) 조합을 돌려 결과 리스트 반환 (fast < slow 만)."""
    rows = []
    for fast in FASTS:
        for slow in SLOWS:
            if fast >= slow:
                continue
            d = df.copy()
            d[f"ma{fast}"] = d["close"].rolling(fast).mean()
            d[f"ma{slow}"] = d["close"].rolling(slow).mean()
            r = run_backtest(d, fast=fast, slow=slow, fee=FEE)
            rows.append({
                "fast": fast, "slow": slow,
                "return": r["strategy_return"],
                "trades": r["num_trades"],
                "win_rate": r["win_rate"],
            })
    return pd.DataFrame(rows).sort_values("return", ascending=False).reset_index(drop=True)


def main():
    ex = make_exchange()
    df = fetch_candles(ex, timeframe=TIMEFRAME, limit=LIMIT)
    print(f"[데이터] {SYMBOL} {TIMEFRAME}  {len(df)}개  "
          f"({df['time'].iloc[0].date()} ~ {df['time'].iloc[-1].date()})")
    bh = df['close'].iloc[-1] / df['close'].iloc[0] - 1
    print(f"[비교군] 그냥 보유(Buy&Hold) 수익률: {bh*100:+.2f}%\n")

    # 1) 전체 기간 성적표
    table = sweep(df)
    print("=== 전체 기간 성적표 (상위 8) ===")
    top = table.head(8).copy()
    top["return"] = (top["return"] * 100).round(2).astype(str) + "%"
    top["win_rate"] = (top["win_rate"] * 100).round(1).astype(str) + "%"
    print(top.to_string(index=False))

    # 2) 과최적화 검증: 앞 70% 로 최적화 → 뒤 30% 로 시험
    split = int(len(df) * 0.7)
    train, test = df.iloc[:split].reset_index(drop=True), df.iloc[split:].reset_index(drop=True)

    best = sweep(train).iloc[0]
    f, s = int(best["fast"]), int(best["slow"])

    d = test.copy()
    d[f"ma{f}"] = d["close"].rolling(f).mean()
    d[f"ma{s}"] = d["close"].rolling(s).mean()
    test_r = run_backtest(d, fast=f, slow=s, fee=FEE)
    test_bh = test['close'].iloc[-1] / test['close'].iloc[0] - 1

    print("\n=== 과최적화 검증 (train 70% → test 30%) ===")
    print(f"train 1등 조합 : MA{f}/{s}  (train 수익률 {best['return']*100:+.2f}%)")
    print(f"→ test 수익률  : {test_r['strategy_return']*100:+.2f}%   "
          f"(같은 기간 그냥 보유 {test_bh*100:+.2f}%)")
    if test_r["strategy_return"] > test_bh and test_r["strategy_return"] > 0:
        print("판정: test 에서도 살아남음 (드문 경우)")
    else:
        print("판정: test 에서 무너짐 ❌  → train 에서 '1등'은 대개 우연/과최적화")


if __name__ == "__main__":
    main()
