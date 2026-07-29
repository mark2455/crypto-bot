"""
Connors RSI 롱/숏 대칭 버전 검증.
롱: CRSI<buy_th(과매도) & 가격>MA200(상승추세) → 매수, CRSI>exit_th 청산
숏: CRSI>(100-buy_th)(과매수) & 가격<MA200(하락추세) → 매도, CRSI<(100-exit_th) 청산
(롱온리 버전과 동일하게 레버리지 없음, 수수료만 반영 — 방향만 대칭 추가)

실행:  ~/crypto-bot/venv/bin/python connors_ls_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv
from connors_rsi_backtest import connors_rsi

FEE = 0.0004
MAX_HOLD = 100


def run_ls(df, buy_th=10, exit_th=50, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    crsi = connors_rsi(close)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th = 100 - buy_th
    cover_th = 100 - exit_th

    trades_long, trades_short = [], []
    side = 0            # 0=없음, 1=롱, -1=숏
    entry = 0.0
    held = 0
    i = 250
    while i < len(close):
        if side != 0:
            held += 1
            if side == 1 and (crsi[i] > exit_th or held >= MAX_HOLD):
                net = close[i] / entry - 1 - 2 * FEE
                trades_long.append(net); side = 0
            elif side == -1 and (crsi[i] < cover_th or held >= MAX_HOLD):
                net = 1 - close[i] / entry - 2 * FEE
                trades_short.append(net); side = 0
            i += 1
            continue

        if crsi[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and crsi[i] > sell_th and close[i] < ma200[i]:
            side, entry, held = -1, close[i], 0
        i += 1

    all_trades = trades_long + trades_short   # 시간순은 아니지만 전체 곱연산엔 순서 무관(복리 근사)
    equity = np.prod(1 + np.array(all_trades)) if all_trades else 1.0
    wins = [t for t in all_trades if t > 0]
    return {
        "n_long": len(trades_long), "n_short": len(trades_short),
        "win_rate": (len(wins) / len(all_trades) * 100) if all_trades else 0,
        "return": (equity - 1) * 100,
        "long_ret": (np.prod(1 + np.array(trades_long)) - 1) * 100 if trades_long else 0,
        "short_ret": (np.prod(1 + np.array(trades_short)) - 1) * 100 if trades_short else 0,
    }


def main():
    print("=== Connors RSI 롱온리 vs 롱숏대칭 (2년 전체, buy=10 exit=50, 수수료반영) ===\n")
    for coin in ["DOTUSDT", "LTCUSDT"]:
        df = load_candles_csv(f"data/{coin}_1h.csv")
        bh = df["close"].iloc[-1] / df["close"].iloc[0] - 1
        print(f"[{coin.replace('USDT','')}]  (그냥 보유 2년: {bh*100:+.2f}%)")

        r_long = run_ls(df, allow_short=False)
        print(f"  롱온리   : 거래(롱{r_long['n_long']}/숏0)  수익 {r_long['return']:+7.2f}%")

        r_ls = run_ls(df, allow_short=True)
        print(f"  롱숏대칭 : 거래(롱{r_ls['n_long']}/숏{r_ls['n_short']})  "
              f"전체수익 {r_ls['return']:+7.2f}%  (롱부분 {r_ls['long_ret']:+.2f}% / 숏부분 {r_ls['short_ret']:+.2f}%)")
        print()


if __name__ == "__main__":
    main()
