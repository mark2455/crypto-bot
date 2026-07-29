"""
지표 신호 분석: 특정 전략을 정하지 않고, '지표가 이 상태일 때 실제로 얼마나 자주/얼마나
크게 올랐는지(또는 내렸는지)'를 데이터로 직접 뽑아본다.

대상: BTC, ETH 최근 1년(8760시간) 1시간봉.
지표: RSI(14), MACD, 볼린저밴드 %B, MA배열(단기/장기, 골든·데드크로스),
      스토캐스틱, ADX(추세강도), 거래량(20기간 평균 대비).
방법: 각 지표를 몇 개 구간(regime)으로 나누고, 그 구간에 있을 때의
      '다음 24시간 수익률' 평균·승률·표본수를 계산. (지표는 항상 과거 데이터로만 계산 → lookahead 없음)

실행:  ~/crypto-bot/venv/bin/python indicator_analysis.py
"""
import os
import numpy as np
import pandas as pd
from candles import load_candles_csv

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
HORIZON = 24        # 다음 24시간 수익률로 평가
ONE_YEAR = 24 * 365


def rsi(close, period=14):
    delta = np.diff(close, prepend=close[0])
    gain = np.clip(delta, 0, None); loss = np.clip(-delta, 0, None)
    ag = pd.Series(gain).ewm(alpha=1/period, adjust=False).mean().to_numpy()
    al = pd.Series(loss).ewm(alpha=1/period, adjust=False).mean().to_numpy()
    rs = np.divide(ag, al, out=np.full_like(close, np.inf), where=al != 0)
    return 100 - 100 / (1 + rs)


def macd(close, fast=12, slow=26, signal=9):
    s = pd.Series(close)
    ema_f = s.ewm(span=fast, adjust=False).mean()
    ema_s = s.ewm(span=slow, adjust=False).mean()
    line = ema_f - ema_s
    sig = line.ewm(span=signal, adjust=False).mean()
    return (line - sig).to_numpy()          # 히스토그램(양수=상승모멘텀)


def bollinger_pctb(close, period=20, k=2):
    s = pd.Series(close)
    ma = s.rolling(period).mean()
    sd = s.rolling(period).std()
    upper, lower = ma + k * sd, ma - k * sd
    pctb = (s - lower) / (upper - lower)     # 0=하단, 1=상단, <0/>1 이탈
    return pctb.to_numpy()


def stochastic(high, low, close, period=14, smooth=3):
    h = pd.Series(high).rolling(period).max()
    l = pd.Series(low).rolling(period).min()
    k = 100 * (pd.Series(close) - l) / (h - l)
    return k.rolling(smooth).mean().to_numpy()


def adx(high, low, close, period=14):
    h, l, c = pd.Series(high), pd.Series(low), pd.Series(close)
    up = h.diff(); down = -l.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm).ewm(alpha=1/period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).ewm(alpha=1/period, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.ewm(alpha=1/period, adjust=False).mean().to_numpy()


def build(df):
    close = df["close"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    vol = df["volume"].to_numpy(dtype=float)
    n = len(close)

    ma20 = pd.Series(close).rolling(20).mean().to_numpy()
    ma50 = pd.Series(close).rolling(50).mean().to_numpy()
    ma200 = pd.Series(close).rolling(200).mean().to_numpy()
    vol_ma20 = pd.Series(vol).rolling(20).mean().to_numpy()

    fwd_ret = np.full(n, np.nan)
    fwd_ret[:-HORIZON] = close[HORIZON:] / close[:-HORIZON] - 1

    return pd.DataFrame({
        "close": close, "fwd_ret": fwd_ret,
        "rsi": rsi(close),
        "macd_hist": macd(close),
        "pctb": bollinger_pctb(close),
        "stoch": stochastic(high, low, close),
        "adx": adx(high, low, close),
        "ma20_above_ma50": ma20 > ma50,
        "price_above_ma200": close > ma200,
        "vol_ratio": vol / vol_ma20,
    })


def regime_stats(d, col, bins, labels):
    d = d.dropna(subset=[col, "fwd_ret"])
    cats = pd.cut(d[col], bins=bins, labels=labels)
    rows = []
    for lab in labels:
        sub = d[cats == lab]
        if len(sub) == 0:
            continue
        rows.append((lab, len(sub), sub["fwd_ret"].mean() * 100,
                     (sub["fwd_ret"] > 0).mean() * 100))
    return rows


def bool_stats(d, col):
    d = d.dropna(subset=[col, "fwd_ret"])
    rows = []
    for val in [True, False]:
        sub = d[d[col] == val]
        if len(sub) == 0:
            continue
        rows.append((str(val), len(sub), sub["fwd_ret"].mean() * 100,
                     (sub["fwd_ret"] > 0).mean() * 100))
    return rows


def print_rows(title, rows):
    print(f"  [{title}]")
    for lab, n, avg, wr in rows:
        arrow = "▲" if avg > 0 else "▼"
        print(f"    {lab:16} 표본 {n:>5}  다음24h 평균수익 {avg:+6.2f}% {arrow}  상승확률 {wr:5.1f}%")


def analyze(coin, df):
    print(f"\n{'='*78}\n[{coin}] 최근 1년 ({df['time'].iloc[0].date()} ~ {df['time'].iloc[-1].date()})  "
          f"— 다음 {HORIZON}시간 수익률 기준\n{'='*78}")
    d = build(df)

    print_rows("RSI(14)", regime_stats(d, "rsi", [-1, 30, 45, 55, 70, 101],
               ["과매도(<30)", "약세(30-45)", "중립(45-55)", "강세(55-70)", "과매수(>70)"]))
    print_rows("MACD 히스토그램", regime_stats(d, "macd_hist",
               [-1e9, -close_scale(d), 0, close_scale(d), 1e9],
               ["강한음(모멘텀↓↓)", "약한음", "약한양", "강한양(모멘텀↑↑)"]))
    print_rows("볼린저 %B", regime_stats(d, "pctb", [-10, 0, 0.3, 0.7, 1, 10],
               ["하단이탈(<0)", "하단권(0-0.3)", "중앙권(0.3-0.7)", "상단권(0.7-1)", "상단이탈(>1)"]))
    print_rows("스토캐스틱", regime_stats(d, "stoch", [-1, 20, 50, 80, 101],
               ["과매도(<20)", "약세(20-50)", "강세(50-80)", "과매수(>80)"]))
    print_rows("ADX(추세강도)", regime_stats(d, "adx", [-1, 15, 25, 40, 1000],
               ["추세없음(<15)", "약한추세(15-25)", "뚜렷한추세(25-40)", "강한추세(>40)"]))
    print_rows("MA20 vs MA50", bool_stats(d, "ma20_above_ma50"))
    print_rows("가격 vs MA200(장기추세)", bool_stats(d, "price_above_ma200"))
    print_rows("거래량(20기간 평균 대비)", regime_stats(d, "vol_ratio", [0, 0.7, 1.3, 2, 1000],
               ["저조(<0.7배)", "평균(0.7-1.3배)", "급증(1.3-2배)", "폭증(>2배)"]))


def close_scale(d):
    """MACD 임계값을 코인별 가격 스케일에 맞게(중앙값 0.05% 정도) 잡기 위한 헬퍼."""
    return d["close"].median() * 0.0005


def main():
    for coin in ["BTCUSDT", "ETHUSDT"]:
        df = load_candles_csv(os.path.join(DATA_DIR, f"{coin}_1h.csv")).tail(ONE_YEAR).reset_index(drop=True)
        analyze(coin.replace("USDT", ""), df)


if __name__ == "__main__":
    main()
