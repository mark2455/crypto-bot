"""
교차검증: RSI(2) 평균회귀 전략을 BTC/ETH/SOL 에 똑같이 돌려 비교한다.
- 진짜 우위라면 세 코인에서 비슷하게 나와야 한다.
- 세 코인 모두 손실이면 "이 전략은 확실히 안 된다"는 강한 결론.

실행:  ~/crypto-bot/venv/bin/python multicoin_rsi.py
"""
import os
from candles import load_candles_csv
from rsi_backtest import run

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def line(coin, tag, r):
    return (f"{coin:8} {tag:6} "
            f"거래 {r['trades']:>4}  승률 {r['win_rate']*100:5.1f}%  "
            f"전략 {r['return']*100:+7.2f}%  보유 {r['buyhold']*100:+7.2f}%  "
            f"최악 {r['worst']*100:+6.2f}%  MDD {r['mdd']*100:6.2f}%")


def main():
    print("=== RSI(2) 평균회귀 · 3코인 교차검증 (수수료 반영) ===\n")
    print(f"{'코인':8} {'구간':6} {'':4}  성적")
    print("-" * 92)
    for coin in COINS:
        df = load_candles_csv(os.path.join(DATA_DIR, f"{coin}_1h.csv"))
        split = int(len(df) * 0.7)
        print(line(coin, "전체", run(df)))
        print(line(coin, "train", run(df.iloc[:split].reset_index(drop=True))))
        print(line(coin, "test", run(df.iloc[split:].reset_index(drop=True))))
        print("-" * 92)


if __name__ == "__main__":
    main()
