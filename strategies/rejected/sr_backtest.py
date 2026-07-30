"""
A단계: 지지/저항 기반 + 손익비(RR) 필터 전략 백테스트.

아이디어(롱 전용, 단순화):
  - 지지(support)  = 최근 스윙 저점(피벗 로우)
  - 저항(resistance) = 최근 스윙 고점(피벗 하이)
  - 가격이 '지지 근처'로 내려오면 진입 후보
  - 손절(SL) = 지지 약간 아래,  목표(TP) = 위쪽 최근접 저항
  - 손익비 RR = (TP-진입)/(진입-SL) 가 기준(예: 5) 이상일 때만 진입
  - 진입 후 SL/TP 중 먼저 닿는 쪽에서 청산 (한 봉에 둘 다면 보수적으로 SL 우선)

왜 RR 필터?  1:5 면 승률이 낮아도 이긴다. 손익분기 승률 = 1/(1+RR).
  RR=5 → 16.7% 만 넘으면 본전. '좋은 자리'만 골라 진입하는 게 목적.

lookahead(미래 훔쳐보기) 방지: 피벗은 좌우 PIVOT 봉으로 확정되므로,
현재 봉 i 에서는 index <= i-PIVOT 인 '확정된' 피벗만 사용한다.

실행:  ~/crypto-bot/venv/bin/python sr_backtest.py
"""
import os
import numpy as np
from config import make_exchange, SYMBOL
from candles import fetch_candles, load_candles_csv

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "BTCUSDT_1h.csv")

TIMEFRAME = "1h"
LIMIT = 1500

PIVOT = 5          # 스윙 고/저점 판정 좌우 봉 수
NEAR = 0.004       # 지지 대비 이 비율(0.4%) 안으로 내려오면 '지지 근처'
BUFFER = 0.005     # 손절을 지지보다 이만큼(0.5%) 더 아래에 둠 — 여유 확대
RR_MIN = 3.0       # 최소 손익비 (1 : RR_MIN)
RISK_PER_TRADE = 0.02   # 거래당 자본의 2% 리스크(포지션 사이징)
FEE = 0.0004       # 진입/청산 1회당 수수료(테이커 0.04%) — 왕복 2회 반영
MA_TREND = 200     # 추세 필터용 이동평균 기간(가격 > MA 일 때만 롱)


def find_pivots(high, low, k=PIVOT):
    """확정된 스윙 고점/저점 인덱스 리스트 반환."""
    hp, lp = [], []
    for i in range(k, len(high) - k):
        if high[i] == max(high[i - k:i + k + 1]):
            hp.append(i)
        if low[i] == min(low[i - k:i + k + 1]):
            lp.append(i)
    return hp, lp


def _close_trade(exit_price, entry, sl_risk):
    """청산 시 '수수료까지 반영한' 순 R 배수를 계산."""
    risk = entry - sl_risk                      # 1R 에 해당하는 가격 거리
    gross_r = (exit_price - entry) / risk        # 수수료 전 R
    # 왕복 수수료를 R 단위로 환산: (진입가+청산가)*FEE / risk
    fee_r = FEE * (entry + exit_price) / risk
    return gross_r - fee_r                        # 순 R


def run(df, rr_min=RR_MIN):
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    ma = df["close"].rolling(MA_TREND).mean().to_numpy()   # 추세 필터용 MA
    hp, lp = find_pivots(high, low)

    equity = 1.0
    in_pos = False
    entry = sl = tp = sl_risk = 0.0
    r_multiples = []   # 거래별 '순' R 배수(수수료 반영)

    start = MA_TREND + 1     # MA 가 채워진 뒤부터 시작
    for i in range(start, len(df)):
        if in_pos:
            if low[i] <= sl:                 # 손절 먼저(보수적)
                r = _close_trade(sl, entry, sl_risk)
                equity *= 1 + RISK_PER_TRADE * r
                r_multiples.append(r)
                in_pos = False
            elif high[i] >= tp:              # 목표 도달
                r = _close_trade(tp, entry, sl_risk)
                equity *= 1 + RISK_PER_TRADE * r
                r_multiples.append(r)
                in_pos = False
            continue

        price = close[i]
        # 조건 ① 추세 필터: 가격이 MA 위(상승 추세)일 때만 롱
        if not (price > ma[i]):
            continue

        # 현재 봉에서 '확정된' 피벗만 사용 (index <= i - PIVOT)
        supports = [low[j] for j in lp if j <= i - PIVOT and low[j] < price]
        resistances = [high[j] for j in hp if j <= i - PIVOT and high[j] > price]
        if not supports or not resistances:
            continue

        support = max(supports)       # 최근접 아래 지지
        resistance = min(resistances) # 최근접 위 저항

        if price <= support * (1 + NEAR):      # 지지 근처로 내려왔나
            cand_sl = support * (1 - BUFFER)
            cand_tp = resistance
            risk = price - cand_sl
            reward = cand_tp - price
            if risk <= 0 or reward <= 0:
                continue
            if reward / risk >= rr_min:        # 조건 ② 손익비 필터
                in_pos = True
                entry, sl, tp = price, cand_sl, cand_tp
                sl_risk = cand_sl              # R 계산용 손절가

    wins = [r for r in r_multiples if r > 0]
    bh = close[-1] / close[start] - 1
    return {
        "trades": len(r_multiples),
        "win_rate": (len(wins) / len(r_multiples)) if r_multiples else 0.0,
        "total_R": sum(r_multiples),
        "return": equity - 1,
        "buyhold": bh,
        "breakeven_wr": 1 / (1 + rr_min),
    }


def show(title, r):
    print(f"=== {title} ===")
    if r["trades"] == 0:
        print("진입 0회 — 조건(RR>=5 인 자리)이 이 기간엔 없었음\n")
        return
    print(f"진입 횟수     : {r['trades']}회")
    print(f"승률          : {r['win_rate']*100:.1f}%   (본전 승률 {r['breakeven_wr']*100:.1f}%)")
    print(f"누적 R        : {r['total_R']:+.2f} R")
    print(f"전략 수익률   : {r['return']*100:+.2f}%   (거래당 {RISK_PER_TRADE*100:.0f}% 리스크)")
    print(f"그냥 보유     : {r['buyhold']*100:+.2f}%\n")


def main():
    # 대량 CSV 가 있으면 그걸 쓰고(2년치), 없으면 테스트넷 실시간(1000개)
    if os.path.exists(CSV_PATH):
        df = load_candles_csv(CSV_PATH)
        print(f"[데이터] CSV 사용: {len(df)}개")
    else:
        ex = make_exchange()
        df = fetch_candles(ex, timeframe=TIMEFRAME, limit=LIMIT)
    print(f"[데이터] {SYMBOL} {TIMEFRAME}  {len(df)}개  "
          f"({df['time'].iloc[0].date()} ~ {df['time'].iloc[-1].date()})")
    print(f"[설정] 지지근처 {NEAR*100:.1f}% / 손절버퍼 {BUFFER*100:.1f}% / 최소RR {RR_MIN} "
          f"/ 추세필터 MA{MA_TREND} / 수수료 {FEE*100:.2f}%×왕복\n")

    show("전체 기간", run(df))

    split = int(len(df) * 0.7)
    show("train 70% (앞)", run(df.iloc[:split].reset_index(drop=True)))
    show("test 30% (뒤, 처음 보는 기간)", run(df.iloc[split:].reset_index(drop=True)))


if __name__ == "__main__":
    main()
