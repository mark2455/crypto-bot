"""
indicator_analysis.py 에서 발견한 신호를 실제 매매 규칙으로 백테스트.

발견한 패턴: MACD 히스토그램이 '막 음(-)→양(+)으로 전환'(약한양 구간) +
            MA20 > MA50(골든크로스) 일 때, 다음 24h 수익률이 베이스라인보다 뚜렷이 좋았음.

규칙:
  - 진입(롱): MACD 히스토그램이 방금 0을 넘어 '약한양' 구간에 진입 AND MA20>MA50
  - 청산: 정확히 24시간 뒤 (분석과 동일한 조건으로 검증)
  - 동시 포지션 1개만(겹치지 않음), 수수료 왕복 반영

검증 방법 (중요): '발견에 쓴 최근 1년'과 '발견에 안 쓴 그 이전 1년'을 나눠서 각각 본다.
  - 최근1년(discovery)에서 되는 건 당연할 수 있음(그 데이터로 찾은 패턴이니까)
  - 이전1년(홀드아웃)에서도 되는지가 '진짜 아웃오브샘플' 검증

실행:  ~/crypto-bot/venv/bin/python macd_signal_backtest.py
"""
import os
import numpy as np
from candles import load_candles_csv
from indicator_analysis import build, close_scale, HORIZON, ONE_YEAR

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
FEE = 0.0004


def run(df, use_ma_filter=True):
    d = build(df)
    close = d["close"].to_numpy()
    macd_h = d["macd_hist"].to_numpy()
    ma_ok = d["ma20_above_ma50"].to_numpy()
    thr = close_scale(d)
    n = len(close)

    trades = []
    i = 200   # MA200 등 지표 안정화 이후부터
    while i < n - HORIZON:
        crossed_up = macd_h[i - 1] <= 0 and 0 < macd_h[i] <= thr
        filt_ok = (not use_ma_filter) or ma_ok[i]
        if crossed_up and filt_ok:
            entry = close[i]
            exit_ = close[i + HORIZON]
            net = exit_ / entry - 1 - 2 * FEE
            trades.append(net)
            i += HORIZON            # 겹치지 않게 다음 진입은 청산 이후부터
        else:
            i += 1

    if not trades:
        return {"trades": 0}
    trades = np.array(trades)
    equity = np.prod(1 + trades)
    wins = trades[trades > 0]
    return {
        "trades": len(trades),
        "win_rate": len(wins) / len(trades) * 100,
        "avg": trades.mean() * 100,
        "return": (equity - 1) * 100,
        "worst": trades.min() * 100,
        "best": trades.max() * 100,
    }


def show(tag, r):
    if r["trades"] == 0:
        print(f"  {tag:28} 거래 0"); return
    print(f"  {tag:28} 거래 {r['trades']:>3}  승률 {r['win_rate']:5.1f}%  "
          f"평균 {r['avg']:+.3f}%  누적수익 {r['return']:+7.2f}%  "
          f"최고/최악 {r['best']:+.2f}%/{r['worst']:+.2f}%")


def main():
    print(f"=== MACD 약전환 + MA20>MA50 신호 백테스트 (보유 {HORIZON}h, 수수료 {FEE*100:.2f}%×2) ===")
    for coin in ["BTCUSDT", "ETHUSDT"]:
        full = load_candles_csv(os.path.join(DATA_DIR, f"{coin}_1h.csv"))
        discovery = full.tail(ONE_YEAR).reset_index(drop=True)      # 발견에 쓴 최근 1년
        holdout = full.head(len(full) - ONE_YEAR).reset_index(drop=True)  # 발견에 안 쓴 이전 1년

        print(f"\n[{coin.replace('USDT','')}]")
        print(" 발견 구간(최근1년, 2025-07~2026-07):")
        show("  필터 포함(MA20>MA50)", run(discovery, True))
        show("  필터 없음(MACD만)", run(discovery, False))
        print(" 홀드아웃(이전1년, 2024-07~2025-07, 진짜 검증):")
        show("  필터 포함(MA20>MA50)", run(holdout, True))
        show("  필터 없음(MACD만)", run(holdout, False))


if __name__ == "__main__":
    main()
