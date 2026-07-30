"""
[확정 전략] Connors RSI 롱숏대칭 — DOT / LINK / ETC 전용

검증 이력 (2026-07-29 기준):
  - 1시간봉, buy_th=10, exit_th=50, MAX_HOLD=100시간, 왕복수수료 0.08%
  - 4년치(2022-07~2026-07) 4개 연도 구간(하락/강세/횡보 혼재)에서 전부 검증
  - DOT: 4/4년 플러스, 4년 합계 +53.75%  (그냥 보유 -90.98%)
  - LINK: 4/4년 플러스, 4년 합계 +46.14% (그냥 보유  +7.46%, 보유도 이김)
  - ETC: 4/4년 플러스, 4년 합계 +15.32%  (그냥 보유 -83.24%)
  - LTC: 3/4년 플러스 (강세장에 약함) → 참고용, 미확정
  - XRP: 1/4년만 플러스, 4년 합계 -0.01% → 탈락 (단기 검증에서 우연히 좋아 보였음)
  - 파라미터 견고성: buy_th∈[5,10] 구간에서 exit_th 무관하게 안정적 (buy_th 15~20은 국면 의존적 불안정 → 사용 금지)

규칙:
  롱: CRSI(3,2,100) < buy_th (과매도) AND 종가 > MA200(상승추세) → 매수
      청산: CRSI > exit_th 또는 MAX_HOLD 경과
  숏: CRSI > (100-buy_th) (과매수) AND 종가 < MA200(하락추세) → 매도
      청산: CRSI < (100-exit_th) 또는 MAX_HOLD 경과

원본 구현: ../connors_rsi_backtest.py (지표), ../connors_ls_backtest.py (롱숏 실행)
"""

CONFIRMED_COINS = ["DOTUSDT", "LINKUSDT", "ETCUSDT"]   # 검증 통과
WATCH_COINS = ["LTCUSDT"]                               # 참고용(강세장 약함)
REJECTED_COINS = ["XRPUSDT"]                             # 탈락(우연이었음)

PARAMS = {
    "rsi_period": 3,
    "streak_period": 2,
    "roc_period": 100,
    "buy_th": 10,
    "exit_th": 50,
    "ma_trend": 200,
    "max_hold_hours": 100,
    "fee_per_side": 0.0004,
}

from connors_ls_backtest import run_ls  # noqa: E402  (재사용 편의를 위한 재노출)
from connors_rsi_backtest import connors_rsi  # noqa: E402
