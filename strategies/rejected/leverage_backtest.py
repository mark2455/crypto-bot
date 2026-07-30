"""
롱/숏 대칭 + 레버리지 백테스트 (청산 모델 포함).

전략(RSI 평균회귀를 롱·숏 대칭으로):
  - 롱  진입: RSI(2) < RSI_BUY  그리고 종가 > MA_TREND (상승추세)  → 청산: 종가 > MA_EXIT
  - 숏  진입: RSI(2) > RSI_SELL 그리고 종가 < MA_TREND (하락추세)  → 청산: 종가 < MA_EXIT
    (숏은 롱의 '정반대 조건')

레버리지의 핵심 = 청산(liquidation):
  - 롱: 가격이 진입가의 (1 - 1/L) 아래로 닿으면 청산 → 그 거래에서 증거금 100% 손실
  - 숏: 가격이 진입가의 (1 + 1/L) 위로 닿으면 청산 → 마찬가지
  - 즉 10배면 약 10% 역행에 계좌가 날아간다. 이걸 봉의 고/저가로 정직하게 검사한다.

가정: 거래마다 '전액'을 증거금으로 투입(단순화). 그래서 한 번 청산 = 사실상 계좌 전멸.
실행:  ~/crypto-bot/venv/bin/python leverage_backtest.py
"""
import os
from candles import load_candles_csv
from rsi_backtest import rsi, sma, RSI_LEN, MA_TREND, MA_EXIT, FEE, MAX_HOLD

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

RSI_BUY = 10        # 이 아래 = 과매도 → 롱
RSI_SELL = 90       # 이 위  = 과매수 → 숏
LEVERAGE = 3        # ★ 당신이 정하는 레버리지 배율
STOP_LOSS = 0.05    # ★ 최대 손절: 진입가 대비 이만큼(5%) 역행하면 강제 청산 (0 = 손절 없음)


def run_ls(df, leverage=LEVERAGE, stop_loss=STOP_LOSS):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    r = rsi(close, RSI_LEN)
    ma_t = sma(close, MA_TREND)
    ma_x = sma(close, MA_EXIT)

    equity = 1.0
    peak = 1.0
    mdd = 0.0
    side = 0            # 0=없음, +1=롱, -1=숏
    entry = 0.0
    held = 0
    liq_long = 0.0
    liq_short = 0.0
    stop_long = 0.0
    stop_short = 0.0
    trades = []
    holds = []          # 거래별 보유 봉(=시간) 수
    liquidations = 0
    stopped = 0
    reversed_out = 0    # 추세(MA200) 역전으로 청산한 횟수

    def settle(exit_price):
        """청산가/청산이 아닌 정상 종료 시 equity 갱신."""
        nonlocal equity, peak, mdd
        if side == 1:
            move = exit_price / entry - 1
        else:
            move = 1 - exit_price / entry
        mult = 1 + leverage * move - 2 * FEE * leverage   # 레버리지·왕복수수료
        mult = max(mult, 0.0)
        equity *= mult
        trades.append(mult - 1)
        holds.append(held)
        peak = max(peak, equity)
        mdd = min(mdd, equity / peak - 1)

    for i in range(MA_TREND, len(close)):
        if side != 0:
            held += 1
            # 0) 손절 먼저 검사 (청산보다 타이트하므로 우선) — 손절가에서 청산
            if stop_loss > 0:
                if side == 1 and low[i] <= stop_long:
                    settle(stop_long); side = 0; stopped += 1; continue
                if side == -1 and high[i] >= stop_short:
                    settle(stop_short); side = 0; stopped += 1; continue
            # 1) 청산 검사 (봉 내 고/저가)
            if side == 1 and low[i] <= liq_long:
                equity *= 0.0                # 증거금 전액 손실
                trades.append(-1.0); holds.append(held)
                liquidations += 1
                side = 0
                continue
            if side == -1 and high[i] >= liq_short:
                equity *= 0.0
                trades.append(-1.0); holds.append(held)
                liquidations += 1
                side = 0
                continue
            # 2) 추세 역전 손절: 진입 근거였던 MA200 을 반대로 돌파하면 청산
            if side == 1 and close[i] < ma_t[i]:
                settle(close[i]); side = 0; reversed_out += 1; continue
            if side == -1 and close[i] > ma_t[i]:
                settle(close[i]); side = 0; reversed_out += 1; continue
            # 3) 정상 청산 조건 (MA5 반등 익절)
            if side == 1 and (close[i] > ma_x[i] or held >= MAX_HOLD):
                settle(close[i]); side = 0
            elif side == -1 and (close[i] < ma_x[i] or held >= MAX_HOLD):
                settle(close[i]); side = 0
            continue

        if equity <= 1e-6:      # 이미 전멸했으면 더 진입 불가
            break

        # 진입 (롱 우선, 조건 겹치지 않음)
        if r[i] < RSI_BUY and close[i] > ma_t[i]:
            side, entry, held = 1, close[i], 0
            liq_long = entry * (1 - 1 / leverage)
            stop_long = entry * (1 - stop_loss)
        elif r[i] > RSI_SELL and close[i] < ma_t[i]:
            side, entry, held = -1, close[i], 0
            liq_short = entry * (1 + 1 / leverage)
            stop_short = entry * (1 + stop_loss)

    if side != 0:
        settle(close[-1])

    wins = [t for t in trades if t > 0]
    bh = close[-1] / close[MA_TREND] - 1
    sh = sorted(holds)
    return {
        "trades": len(trades), "liq": liquidations, "stopped": stopped,
        "reversed": reversed_out,
        "win_rate": (len(wins) / len(trades)) if trades else 0.0,
        "return": equity - 1, "buyhold": bh,
        "worst": min(trades) if trades else 0.0, "mdd": mdd,
        "avg_hold": (sum(holds) / len(holds)) if holds else 0.0,
        "med_hold": sh[len(sh) // 2] if sh else 0,
        "max_hold": max(holds) if holds else 0,
    }


def row(tag, r):
    return (f"{tag:14} 거래 {r['trades']:>4}  손절 {r['stopped']:>4}  역전 {r['reversed']:>4}  "
            f"승률 {r['win_rate']*100:5.1f}%  전략 {r['return']*100:+8.2f}%  "
            f"최악 {r['worst']*100:+6.2f}%  MDD {r['mdd']*100:7.2f}%")


def main():
    print(f"=== 롱/숏 + 레버리지 {LEVERAGE}배 + 손절 {STOP_LOSS*100:.0f}% + MA200 역전손절  (RSI 평균회귀) ===\n")
    for coin in COINS:
        df = load_candles_csv(os.path.join(DATA_DIR, f"{coin}_1h.csv"))
        print(row(coin, run_ls(df, LEVERAGE, STOP_LOSS)))

    print(f"\n=== 평균 보유 기간 (1봉 = 1시간) ===\n")
    for coin in COINS:
        df = load_candles_csv(os.path.join(DATA_DIR, f"{coin}_1h.csv"))
        r = run_ls(df, LEVERAGE, STOP_LOSS)
        print(f"{coin:10} 평균 {r['avg_hold']:5.1f}시간  중앙값 {r['med_hold']:>3}시간  "
              f"최장 {r['max_hold']:>3}시간")

    df = load_candles_csv(os.path.join(DATA_DIR, "BTCUSDT_1h.csv"))
    print(f"\n=== 손절 스윕 (BTC, 레버리지 {LEVERAGE}배 고정) — 손절이 도움되나? ===\n")
    for sl in [0.0, 0.01, 0.02, 0.03, 0.05, 0.10]:
        tag = "손절없음" if sl == 0 else f"손절 {sl*100:.0f}%"
        print(row(tag, run_ls(df, LEVERAGE, sl)))


if __name__ == "__main__":
    main()
