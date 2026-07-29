"""
시간대(UTC) 계절성 검증 — 지표가 아니라 '언제 거래하느냐'는 구조적 이상현상.
학술 주장(QuantPedia 등): UTC 22~23시가 가장 좋고, 3~4시가 가장 나쁘다.

방법:
  1) 각 UTC 시간대(0~23)별 '그 시간 봉의 수익률' 평균·승률을 전체 데이터로 계산
     (이건 파라미터 최적화가 아니라 단순 관측이라 과최적화 위험이 적음)
  2) 학술 주장 그대로 규칙화: 'UTC 22~23시만 롱 보유, 나머지는 현금' 전략을
     수수료 반영해서 train(전반부)/test(후반부) + 여러 코인으로 검증

주의: candles.py 는 시간을 한국시간(KST)으로 바꾸므로, 여기선 원본 UTC 를 다시 사용.

실행:  ~/crypto-bot/venv/bin/python hour_seasonality.py
"""
import os
import glob
import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FEE = 0.0004


def load_utc(path):
    df = pd.read_csv(path, parse_dates=["time"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def hour_table(df):
    d = df.copy()
    d["ret"] = d["close"] / d["close"].shift(1) - 1
    d["hour"] = d["time"].dt.hour
    g = d.groupby("hour")["ret"].agg(["mean", "count", lambda x: (x > 0).mean()])
    g.columns = ["mean_ret", "n", "win_rate"]
    return g


def strategy_hours_only(df, good_hours, split=None):
    """good_hours 시간대에만 롱 보유, 그 외 시간엔 현금(포지션 없음)."""
    d = df.copy()
    d["ret"] = d["close"] / d["close"].shift(1) - 1
    d["hour"] = d["time"].dt.hour
    if split is not None:
        d = d.iloc[split[0]:split[1]]
    in_good = d["hour"].isin(good_hours)
    # 진입/청산 시점(진입해서 처음 좋은시간 들어간 봉, 마지막 좋은시간 나온 봉)마다 수수료
    entries = in_good & ~in_good.shift(1, fill_value=False)
    exits = in_good & ~in_good.shift(-1, fill_value=False)
    gross = (d["ret"].where(in_good, 0)).sum()
    n_round_trips = entries.sum()
    net = gross - n_round_trips * 2 * FEE
    bh = d["close"].iloc[-1] / d["close"].iloc[0] - 1
    return {"gross": gross * 100, "net": net * 100, "trips": int(n_round_trips), "bh": bh * 100}


def main():
    print("=== UTC 시간대별 평균 수익률 (BTC, ETH, 전체 2년) ===\n")
    for coin in ["BTCUSDT", "ETHUSDT"]:
        df = load_utc(os.path.join(DATA_DIR, f"{coin}_1h.csv"))
        g = hour_table(df)
        print(f"[{coin.replace('USDT','')}] 상위5 시간대 (평균수익률 기준)")
        top = g.sort_values("mean_ret", ascending=False)
        for h, row in top.head(5).iterrows():
            print(f"  {h:2}시(UTC)  평균 {row.mean_ret*100:+.4f}%  승률 {row.win_rate*100:5.1f}%  표본 {int(row.n)}")
        print(f"[{coin.replace('USDT','')}] 하위5 시간대")
        for h, row in top.tail(5).iterrows():
            print(f"  {h:2}시(UTC)  평균 {row.mean_ret*100:+.4f}%  승률 {row.win_rate*100:5.1f}%  표본 {int(row.n)}")
        print()

    print("\n=== 학술 주장 그대로 규칙화: 'UTC 22~23시만 보유' 전략 검증 ===\n")
    GOOD = [22, 23]
    for coin in ["BTCUSDT", "ETHUSDT"]:
        df = load_utc(os.path.join(DATA_DIR, f"{coin}_1h.csv"))
        n = len(df); half = n // 2
        r_train = strategy_hours_only(df, GOOD, (0, half))
        r_test = strategy_hours_only(df, GOOD, (half, n))
        print(f"[{coin.replace('USDT','')}]")
        print(f"  train: 왕복{r_train['trips']:>4}회  총수익(수수료전) {r_train['gross']:+7.2f}%  "
              f"수수료반영 {r_train['net']:+7.2f}%  (같은기간 보유 {r_train['bh']:+7.2f}%)")
        print(f"  test : 왕복{r_test['trips']:>4}회  총수익(수수료전) {r_test['gross']:+7.2f}%  "
              f"수수료반영 {r_test['net']:+7.2f}%  (같은기간 보유 {r_test['bh']:+7.2f}%)")

    print("\n=== 14개 코인 전체 확장 (UTC 22~23시만 보유, 수수료반영) ===\n")
    both_pos = 0
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*_1h.csv")))
    for path in files:
        coin = os.path.basename(path).split("_")[0].replace("USDT", "")
        df = load_utc(path)
        n = len(df); half = n // 2
        r_train = strategy_hours_only(df, GOOD, (0, half))
        r_test = strategy_hours_only(df, GOOD, (half, n))
        flag = "★둘다+" if (r_train["net"] > 0 and r_test["net"] > 0) else ""
        if flag:
            both_pos += 1
        print(f"  {coin:6} train {r_train['net']:+7.2f}%   test {r_test['net']:+7.2f}%   {flag}")
    print(f"\n→ 14개 중 {both_pos}개 코인에서 두 기간 다 플러스")


if __name__ == "__main__":
    main()
