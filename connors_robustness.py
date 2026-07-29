"""
Connors RSI 통과 코인(ATOM, BCH, DOT, LINK, LTC, XRP)의 파라미터 견고성 검증.

정확히 buy_th=10, exit_th=50 일 때만 되고 살짝만 바꿔도 깨지면 → 과최적화/우연.
주변 파라미터에서도 대체로 되면 → 진짜 신호일 가능성.

buy_th × exit_th 격자(4×4=16조합)를 돌려서, 각 코인마다 '발견구간·홀드아웃 둘 다 플러스'인
조합이 몇 개나 되는지 비율로 확인 (16개 중 다수면 견고, 1~2개뿐이면 우연).

실행:  ~/crypto-bot/venv/bin/python connors_robustness.py
"""
import os
from candles import load_candles_csv
from connors_rsi_backtest import run
from indicator_analysis import ONE_YEAR

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
COINS = ["ATOMUSDT", "BCHUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT", "XRPUSDT"]
BUY_THS = [5, 10, 15, 20]
EXIT_THS = [40, 50, 60, 70]


def main():
    print("=== Connors RSI 파라미터 견고성 (buy_th × exit_th 4×4=16조합) ===")
    print("    (원래 통과했던 buy_th=10,exit_th=50 이 별표)\n")

    for coin in COINS:
        full = load_candles_csv(os.path.join(DATA_DIR, f"{coin}_1h.csv"))
        disc = full.tail(ONE_YEAR).reset_index(drop=True)
        hold = full.head(len(full) - ONE_YEAR).reset_index(drop=True)

        both_pos = 0
        total = 0
        print(f"[{coin.replace('USDT','')}]")
        for bt in BUY_THS:
            row = []
            for et in EXIT_THS:
                if et <= bt:
                    row.append("   -   "); continue
                rd = run(disc, True, buy_th=bt, exit_th=et)
                rh = run(hold, True, buy_th=bt, exit_th=et)
                ok = rd["return"] > 0 and rh["return"] > 0
                total += 1
                if ok:
                    both_pos += 1
                mark = "★" if (bt == 10 and et == 50) else " "
                row.append(f"{'OK' if ok else '--':>3}{mark}")
            print(f"  buy={bt:>2}  " + "  ".join(row))
        print(f"  → {both_pos}/{total} 조합에서 둘 다 플러스  (견고도 {both_pos/total*100:.0f}%)\n")


if __name__ == "__main__":
    main()
