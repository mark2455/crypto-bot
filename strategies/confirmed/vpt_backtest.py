"""
[루프 61회차] Volume Price Trend (VPT) — 거래량에 "가격 변화율(%)"을 곱해서 누적.
OBV(방향 부호만 반영, 크기 무시)·ADL/Chaikin(고가-저가 범위 내 종가 위치 기반)·
Force Index(가격변화 "절대값" × 거래량, 평활 후 사용)와 전부 다른 메커니즘 —
VPT는 유일하게 "퍼센트 변화율"을 거래량에 곱해 누적하므로 코인마다 절대가격이 달라도
스케일이 자동으로 상대화된다(다른 지표들은 절대 가격변화를 쓰므로 코인간 편차가 큼).

VPT[i] = VPT[i-1] + 거래량[i] * (종가[i]-종가[i-1])/종가[i-1]
z = (VPT - 롤링평균200) / 롤링표준편차200

검증 결과 (2026-07-30, 롱숏대칭 기준):
  - LINK: buy_th=−2.0 고정, exit_th −0.5~+0.5 **전체 5칸 연속 4/4** (가장 넓은 단축 블록 사례,
    인접 buy_th −2.5/−3.0 도 전부 3/4로 완만하게 감소 — 절벽 없는 매끄러운 견고 블록)
    최적 buy=−2.0 exit=0.0(또는 0.25, 동일) → 4년 +45.24%, 거래 16건, 승률 75.0% (전 연도 플러스)
  - DOT/XRP/ETC/BTC: 4/4 히트는 있으나 전부 고립셀 또는 대각선 산발 패턴 → 기각
  - 나머지 코인: 4/4 없음
  - LINK 기존 대표(FRAMA 괴리 +301.1%)보다 낮아 헤드라인 교체 없음 — 추가 확정 지표로 등재

실행:  PYTHONPATH=. ~/crypto-bot/venv/bin/python strategies/confirmed/vpt_backtest.py
"""
import numpy as np
import pandas as pd
from candles import load_candles_csv

FEE = 0.0004
MAX_HOLD = 100


def vpt_z(close, volume):
    pct = np.diff(close, prepend=close[0]) / np.roll(close, 1)
    pct[0] = 0.0
    vpt = np.cumsum(volume * pct)
    s = pd.Series(vpt)
    z = (s - s.rolling(200).mean()) / s.rolling(200).std()
    return z.to_numpy()


def run(df, buy_th=-2.0, exit_th=0.0, allow_short=True):
    close = df["close"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    z = vpt_z(close, vol)
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    sell_th, cover_th = -buy_th, -exit_th

    trades = []
    side = 0; entry = 0.0; held = 0
    i = 210
    n = len(close)
    while i < n:
        if np.isnan(z[i]) or np.isnan(ma200[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (z[i] > exit_th or held >= MAX_HOLD):
                trades.append(close[i] / entry - 1 - 2 * FEE); side = 0
            elif side == -1 and (z[i] < cover_th or held >= MAX_HOLD):
                trades.append(1 - close[i] / entry - 2 * FEE); side = 0
            i += 1; continue

        if z[i] < buy_th and close[i] > ma200[i]:
            side, entry, held = 1, close[i], 0
        elif allow_short and z[i] > sell_th and close[i] < ma200[i]:
            side, entry, held = -1, close[i], 0
        i += 1

    if not trades:
        return {"trades": 0, "return": 0.0, "win_rate": 0.0}
    t = np.array(trades)
    return {"trades": len(t), "return": (np.prod(1 + t) - 1) * 100, "win_rate": (t > 0).mean() * 100}


COINS = ["DOTUSDT", "LTCUSDT", "LINKUSDT", "XRPUSDT", "ETCUSDT",
         "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
PERIODS = [("2022-07-30", "2023-07-30"), ("2023-07-30", "2024-07-30"),
           ("2024-07-30", "2025-07-30"), ("2025-07-30", "2026-07-29")]


def grid_search(coin, allow_short):
    df = load_candles_csv(f"data/{coin}_1h_4y.csv")
    buy_ths = [-3.0, -2.5, -2.0, -1.5, -1.0]
    exit_ths = [-0.5, -0.25, 0.0, 0.25, 0.5]
    grid = {}
    for b in buy_ths:
        for e in exit_ths:
            pos = 0
            for start, end in PERIODS:
                mask = (df["time"] >= start) & (df["time"] < end)
                d = df[mask].reset_index(drop=True)
                if len(d) < 500:
                    continue
                r = run(d, buy_th=b, exit_th=e, allow_short=allow_short)
                if r["return"] > 0:
                    pos += 1
            grid[(b, e)] = pos
    return grid, buy_ths, exit_ths


def main():
    df0 = load_candles_csv("data/BTCUSDT_1h_4y.csv")
    z0 = vpt_z(df0["close"].to_numpy(dtype=float), df0["volume"].to_numpy(dtype=float))
    z0v = z0[~np.isnan(z0)]
    print(f"[분포확인] BTC VPT z: 1%={np.percentile(z0v,1):.2f} 5%={np.percentile(z0v,5):.2f} "
          f"95%={np.percentile(z0v,95):.2f} 99%={np.percentile(z0v,99):.2f}\n")

    for coin in COINS:
        for mode_name, allow_short in [("롱온리", False), ("롱숏대칭", True)]:
            grid, buy_ths, exit_ths = grid_search(coin, allow_short)
            best = max(grid.items(), key=lambda kv: kv[1])
            if best[1] == 4:
                hits = [k for k, v in grid.items() if v == 4]
                print(f"{coin.replace('USDT',''):6} {mode_name}: 4/4 히트 {len(hits)}개 -> {hits}")
            else:
                print(f"{coin.replace('USDT',''):6} {mode_name}: 최고 {best[1]}/4 @ {best[0]}")


if __name__ == "__main__":
    main()
