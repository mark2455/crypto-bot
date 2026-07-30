"""
여러 지표를 조합한 신호 백테스트.

기본 트리거(항상 필요): MACD 히스토그램이 막 음(-)→양(+) 전환('약한양' 구간)
여기에 아래 필터들을 하나씩/여러개 조합해서 추가:
  - MA20>MA50 (골든크로스)
  - 가격>MA200 (장기추세)
  - 볼린저 하단이탈 아님 (하단 붕괴 중엔 매수 안 함 — 지표분석에서 최악 구간이었음)
  - ADX>25 (뚜렷한 추세)

각 조합을 '발견구간(최근1년)'과 '홀드아웃(이전1년)' 둘 다에서 테스트해 일관되게
살아남는 조합을 찾는다. 최선 조합은 14개 코인 전체로 확장해 보편성 확인.

실행:  ~/crypto-bot/venv/bin/python combo_signal_backtest.py
"""
import os
import glob
import numpy as np
from candles import load_candles_csv
from indicator_analysis import build, close_scale, HORIZON, ONE_YEAR

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
FEE = 0.0004

COMBOS = {
    "MACD만":                    [],
    "+MA20>MA50":                ["ma_cross"],
    "+가격>MA200":                ["above_ma200"],
    "+MA20>MA50+가격>MA200":      ["ma_cross", "above_ma200"],
    "+MA20>MA50+밴드하단아님":      ["ma_cross", "not_band_break"],
    "+MA20>MA50+ADX>25":         ["ma_cross", "strong_adx"],
    "+전부(MA교차+MA200+ADX+밴드)": ["ma_cross", "above_ma200", "strong_adx", "not_band_break"],
}


def signals(d):
    macd_h = d["macd_hist"].to_numpy()
    thr = close_scale(d)
    trigger = np.zeros(len(d), dtype=bool)
    trigger[1:] = (macd_h[:-1] <= 0) & (macd_h[1:] > 0) & (macd_h[1:] <= thr)
    return {
        "trigger": trigger,
        "ma_cross": d["ma20_above_ma50"].to_numpy(),
        "above_ma200": d["price_above_ma200"].to_numpy(),
        "strong_adx": (d["adx"] > 25).to_numpy(),
        "not_band_break": (d["pctb"] >= 0).to_numpy(),
    }


def run(df, filters):
    d = build(df)
    sig = signals(d)
    close = d["close"].to_numpy()
    n = len(close)
    mask = sig["trigger"].copy()
    for f in filters:
        mask &= sig[f]

    trades = []
    i = 200
    while i < n - HORIZON:
        if mask[i]:
            entry = close[i]; exit_ = close[i + HORIZON]
            trades.append(exit_ / entry - 1 - 2 * FEE)
            i += HORIZON
        else:
            i += 1

    if not trades:
        return {"trades": 0, "return": 0.0, "win_rate": 0.0}
    trades = np.array(trades)
    return {"trades": len(trades), "return": (np.prod(1 + trades) - 1) * 100,
            "win_rate": (trades > 0).mean() * 100}


def main():
    print(f"=== 지표 조합 백테스트 (보유 {HORIZON}h, 수수료 {FEE*100:.2f}%×2) ===\n")
    for coin in ["BTCUSDT", "ETHUSDT"]:
        full = load_candles_csv(os.path.join(DATA_DIR, f"{coin}_1h.csv"))
        disc = full.tail(ONE_YEAR).reset_index(drop=True)
        hold = full.head(len(full) - ONE_YEAR).reset_index(drop=True)
        print(f"[{coin.replace('USDT','')}]")
        print(f"  {'조합':30} {'발견구간':>22} {'홀드아웃(검증)':>22}")
        for name, filters in COMBOS.items():
            rd = run(disc, filters)
            rh = run(hold, filters)
            both_pos = "★둘다+" if (rd["return"] > 0 and rh["return"] > 0) else ""
            print(f"  {name:30} 거래{rd['trades']:>3} {rd['return']:+7.2f}%      "
                  f"거래{rh['trades']:>3} {rh['return']:+7.2f}%   {both_pos}")
        print()


if __name__ == "__main__":
    main()
