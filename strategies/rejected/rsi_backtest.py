"""
B단계: 고승률 전략 검증 — RSI(2) 평균회귀 + 추세필터 (웹 리서치 기반).

전략(롱 전용, Larry Connors 계열):
  - 진입: RSI(2) < RSI_BUY (과매도)  그리고  종가 > MA_TREND (상승추세에서만 = 레짐필터)
  - 청산: 종가 > MA_EXIT (짧은 이평 위로 반등하면 익절)
  - 하드 손절 없음(고전 버전) → 승률은 높지만 '가끔 터지는 큰 손실'이 약점.
    그 약점을 숫자로 드러내려고 '최악의 단일 거래'와 'MDD(최대낙폭)'를 같이 본다.

핵심 질문: 승률은 높다. 그런데 수수료 넣고, 큰 손실까지 세면 실제로 버는가?

실행:  ~/crypto-bot/venv/bin/python rsi_backtest.py
"""
import os
import numpy as np
from config import make_exchange, SYMBOL
from candles import fetch_candles, load_candles_csv

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "BTCUSDT_1h.csv")
TIMEFRAME = "1h"
LIMIT = 1000

RSI_LEN = 2         # RSI 기간(평균회귀는 짧게)
RSI_BUY = 10        # 이 아래면 과매도 → 매수
MA_TREND = 200      # 이 위에 있을 때만 롱(추세/레짐 필터)
MA_EXIT = 5         # 종가가 이 이평 위로 오면 청산
FEE = 0.0004        # 진입/청산 1회당 수수료(0.04%)
MAX_HOLD = 100      # 최대 보유 봉 수(무한정 물리기 방지)


def rsi(close, period):
    delta = np.diff(close, prepend=close[0])
    gain = np.clip(delta, 0, None)
    loss = np.clip(-delta, 0, None)
    # Wilder 스무딩(EMA, alpha=1/period)
    ag = np.zeros_like(close); al = np.zeros_like(close)
    ag[0] = gain[0]; al[0] = loss[0]
    a = 1.0 / period
    for i in range(1, len(close)):
        ag[i] = (1 - a) * ag[i - 1] + a * gain[i]
        al[i] = (1 - a) * al[i - 1] + a * loss[i]
    rs = np.divide(ag, al, out=np.full_like(close, np.inf), where=al != 0)
    return 100 - 100 / (1 + rs)


def sma(close, period):
    out = np.full_like(close, np.nan)
    c = np.cumsum(np.insert(close, 0, 0))
    out[period - 1:] = (c[period:] - c[:-period]) / period
    return out


def run(df):
    close = df["close"].to_numpy(dtype=float)
    r = rsi(close, RSI_LEN)
    ma_t = sma(close, MA_TREND)
    ma_x = sma(close, MA_EXIT)

    equity = 1.0
    peak = 1.0
    mdd = 0.0
    in_pos = False
    entry = 0.0
    held = 0
    trades = []   # 거래별 순수익률(수수료 반영)

    for i in range(MA_TREND, len(close)):
        if in_pos:
            held += 1
            if close[i] > ma_x[i] or held >= MAX_HOLD:   # 청산
                gross = close[i] / entry
                net = gross * (1 - FEE) ** 2               # 왕복 수수료
                equity *= net
                trades.append(net - 1)
                peak = max(peak, equity)
                mdd = min(mdd, equity / peak - 1)
                in_pos = False
            continue

        # 진입: 과매도 + 상승추세
        if r[i] < RSI_BUY and close[i] > ma_t[i]:
            in_pos = True
            entry = close[i]
            held = 0

    if in_pos:   # 남은 포지션 마지막 종가로 청산
        net = close[-1] / entry * (1 - FEE) ** 2
        equity *= net
        trades.append(net - 1)

    wins = [t for t in trades if t > 0]
    bh = close[-1] / close[MA_TREND] - 1
    return {
        "trades": len(trades),
        "win_rate": (len(wins) / len(trades)) if trades else 0.0,
        "return": equity - 1,
        "buyhold": bh,
        "avg_trade": (sum(trades) / len(trades)) if trades else 0.0,
        "worst": min(trades) if trades else 0.0,
        "best": max(trades) if trades else 0.0,
        "mdd": mdd,
    }


def show(title, r):
    print(f"=== {title} ===")
    if r["trades"] == 0:
        print("진입 0회\n"); return
    print(f"진입 횟수     : {r['trades']}회")
    print(f"승률          : {r['win_rate']*100:.1f}%")
    print(f"전략 수익률   : {r['return']*100:+.2f}%   (전액 진입, 수수료 반영)")
    print(f"그냥 보유     : {r['buyhold']*100:+.2f}%")
    print(f"평균 거래     : {r['avg_trade']*100:+.3f}%")
    print(f"최고/최악 거래: {r['best']*100:+.2f}% / {r['worst']*100:+.2f}%  ← 최악이 약점")
    print(f"최대낙폭(MDD) : {r['mdd']*100:.2f}%\n")


def main():
    if os.path.exists(CSV_PATH):
        df = load_candles_csv(CSV_PATH)
    else:
        df = fetch_candles(make_exchange(), timeframe=TIMEFRAME, limit=LIMIT)
    print(f"[데이터] {SYMBOL} {TIMEFRAME}  {len(df)}개  "
          f"({df['time'].iloc[0].date()} ~ {df['time'].iloc[-1].date()})")
    print(f"[전략] RSI({RSI_LEN})<{RSI_BUY} & 종가>MA{MA_TREND} 매수 / 종가>MA{MA_EXIT} 청산 "
          f"/ 수수료 {FEE*100:.2f}%×왕복\n")

    show("전체 기간", run(df))
    split = int(len(df) * 0.7)
    show("train 70% (앞)", run(df.iloc[:split].reset_index(drop=True)))
    show("test 30% (뒤, 처음 보는 기간)", run(df.iloc[split:].reset_index(drop=True)))


if __name__ == "__main__":
    main()
