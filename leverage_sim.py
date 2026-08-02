"""
공용 레버리지/청산 시뮬레이터 — 확정 전략(strategies/confirmed/*.py) 각각의 표준 진입/청산
템플릿(극단값 + MA200 추세필터 + 되돌림청산 + MAX_HOLD)에 맞춰 거래를 봉 인덱스와 함께
추출하고, 격리마진 방식 레버리지(전액 증거금 가정)를 적용해 청산 여부까지 반영한 계좌 곡선을 만든다.

청산 규칙: 롱은 저가가 진입가*(1-1/leverage) 아래로, 숏은 고가가 진입가*(1+1/leverage) 위로
닿으면 그 거래에서 증거금 100% 손실. 전액투입 가정이므로 청산 1회 = 계좌 전멸(그 이후 거래 중단).

실행 예:  PYTHONPATH=. ~/crypto-bot/venv/bin/python -c "..."  (다른 스크립트에서 import해서 사용)
"""
import numpy as np


def extract_trades(close, high, low, ma200, sig, buy_th, sell_th, exit_th, cover_th,
                    allow_short=True, max_hold=100, start_idx=210):
    """표준 템플릿(극단값+MA200필터+되돌림청산+MAX_HOLD) 거래를 봉 인덱스 포함해서 추출."""
    trades = []
    side = 0; entry = 0.0; entry_idx = 0; held = 0
    n = len(close)
    i = start_idx
    while i < n:
        if np.isnan(sig[i]) or np.isnan(ma200[i]):
            i += 1; continue
        if side != 0:
            held += 1
            if side == 1 and (sig[i] > exit_th or held >= max_hold):
                trades.append((1, entry_idx, i, entry, close[i])); side = 0
            elif side == -1 and (sig[i] < cover_th or held >= max_hold):
                trades.append((-1, entry_idx, i, entry, close[i])); side = 0
            i += 1; continue

        if sig[i] < buy_th and close[i] > ma200[i]:
            side, entry, entry_idx, held = 1, close[i], i, 0
        elif allow_short and sig[i] > sell_th and close[i] < ma200[i]:
            side, entry, entry_idx, held = -1, close[i], i, 0
        i += 1
    return trades


def leveraged_equity(trades, high, low, leverage, fee=0.0004):
    """전액투입 가정 — 청산 1회 = 계좌 전멸(이후 거래 중단). 격리마진 청산가로 봉 고/저가 정직 검사."""
    equity = 1.0
    liquidations = 0
    per_trade = []
    wiped = False
    for side, entry_idx, exit_idx, entry_price, exit_price in trades:
        if wiped:
            break
        liq_price = entry_price * (1 - 1 / leverage) if side == 1 else entry_price * (1 + 1 / leverage)
        seg_lo = low[entry_idx + 1:exit_idx + 1]
        seg_hi = high[entry_idx + 1:exit_idx + 1]
        liquidated = (side == 1 and seg_lo.size and seg_lo.min() <= liq_price) or \
                     (side == -1 and seg_hi.size and seg_hi.max() >= liq_price)
        if liquidated:
            equity = 0.0
            per_trade.append(-1.0)
            liquidations += 1
            wiped = True
        else:
            move = exit_price / entry_price - 1 if side == 1 else 1 - exit_price / entry_price
            mult = max(1 + leverage * move - 2 * fee * leverage, 0.0)
            equity *= mult
            per_trade.append(mult - 1)
    return {
        "equity_return": (equity - 1) * 100,
        "liquidations": liquidations,
        "trades_executed": len(per_trade),
        "trades_total": len(trades),
        "wiped": wiped,
    }


def leverage_sweep(trades, high, low, leverages=(1, 2, 3, 5, 7, 10, 15, 20, 30, 50), fee=0.0004):
    rows = []
    for lev in leverages:
        r = leveraged_equity(trades, high, low, lev, fee)
        rows.append((lev, r))
    return rows
