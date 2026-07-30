# 전략 탐색 로그 (/loop 자동 진행)

기준: DOT/LINK/ETC(확정 코인) + BTC/ETH/BNB/SOL/LTC/XRP 9코인, 4년치(2022-07~2026-07)
4개 연도 구간(하락/횡보/강세 혼재) 전부 플러스(4/4)면 통과. 수수료 왕복 0.08% 반영.

## 확정 (통과)
- **Connors RSI 롱숏대칭** (buy_th=10, exit_th=50, MA200 추세필터) — DOT/LINK/ETC 전부 4/4
  파일: strategies/connors_rsi_ls.py

## 기각 (탈락)
| 지표 | 결과 | 비고 |
|---|---|---|
| MA 교차 | 손실 | 최초 시도 |
| RSI(2) 평균회귀 | 손실 | 손익비대칭(이익조기청산/손실방치) |
| MACD 약전환+MA20>MA50 | 우연 수준 | 14코인 중 2개만, 기대값과 일치(다중검정) |
| SuperTrend+ADX | 손실 | TradingView 인기전략 |
| Full Crypto Pack(MACD+RSI+OBV+EMA) | 손실, 승률25~33% | TradingView 인기전략 |
| 삼각수렴 돌파 | 대부분 손실 | 1개 해 몰빵식 착시(XRP 패턴과 동일) |
| 이중바닥/천장, 깃발형, 조합(앙상블) | 손실 또는 표본부족 | 패턴 조합이 Connors 단독보다 항상 나쁨 |
| Ehlers Fisher Transform | 승률 30%, 전코인 손실 | 극단값 필터 적용해도 개선 안됨 |
| **Ehlers Laguerre RSI** | DOT/ETC 전 파라미터 마이너스, LINK 최대 3/4(+62%, buy=0.10 exit=0.85) | 4/4 기준 미달로 기각 |

## 부분 통과 (새 후보로 추가 검토 가치 있음)
- **CMO (Chande Momentum Oscillator, N=14, 평활화 없는 RSI 변형)** — 롱온리
  - **LINK: buy_th=-50 행 전체(exit -20~20 전부) 4/4 견고** ★ — Connors RSI와 별개로 LINK를 재확인
  - **XRP: buy_th=-50~-60, exit_th=-20~0 클러스터 4/4** — Connors RSI에선 탈락했던 XRP가 여기선 통과(새 발견)
  - DOT/SOL/BTC/ETC/LTC/ETH: 격자 전반 불안정 → 기각
  - 롱숏대칭은 XRP/SOL 둘 다 격자에서 고립된 셀(2개뿐)이라 우연 의심, 기각
  파일: cmo_backtest.py

## 기각 (탈락) 추가
| Aroon Oscillator | 전 파라미터에서 항상 정확히 3/4(4/4 불가) | BTC/SOL 최선도 특정 1개 해가 뚫리지 않음. XRP +316%는 3번째로 확인된 "한해 몰빵"패턴(2024-25 XRP 급등 이벤트성) |

| RVI (Relative Vigor Index, 신호선 크로스) | 승률 38~42%(극단값필터 적용해도 개선 안됨), 거의 전멸(-80~99%) | Fisher와 같은 과매매+낮은승률 |

## ⭐ 일반화된 통찰 (설계 원칙)
**"자기 자신의 평활선/지연선과 교차"하는 방식(Fisher Transform, RVI)은 반복적으로 실패한다.**
→ 너무 잦은 휩쏘 + 승률 30~40%대로 방향성 자체가 약함.
**"극단값 도달 후 되돌림"(Connors RSI, CMO)은 상대적으로 훨씬 낫다.**
→ 다음 후보는 전부 이 방식(임계값+되돌림)으로 통일해서 시도할 것.

| MFI (Money Flow Index, 거래량가중 RSI) | DOT 최대 3/4(격자 전체 4/4 없음), 나머지 코인도 대부분 0~2/4 | 극단값+되돌림 방식인데도 거래량 가중이 큰 도움 안 됨 |

| Ultimate Oscillator | 최초 임계값(20) 잘못 잡아 거래 0건 → 재보정(35/50) 후에도 LINK 고립된 1칸만 4/4, 나머지 불안정 | 재보정 교훈: 지표별 실제 분포 확인 필수 |

| Williams %R | 4년차(25-26)가 거의 전코인 persistent 마이너스, DOT 롱숏 3/4가 최선이나 순손실(-40%) | 4/4 없음, 기각 |

## ⭐ 신규 확정 후보 추가
- **TSI (이중평활 모멘텀) 롱온리 — DOT** buy_th=-30, exit_th∈[-5,0,5,10] **네 칸 모두 4/4 견고**
  (buy=-25 도 2칸 4/4). Connors RSI와 별개 지표로 DOT 재확인. 4년합계 +24~39%.
  SOL/BNB 는 3/4가 최선(BNB 고립 1칸 제외)이라 기각. 파일: tsi_backtest.py

## ⭐⭐ 신규 확정 후보 추가 (중요)
- **Elder Ray(추세EMA대비 고/저가 괴리%) 롱온리 — LINK** buy_th=-5, exit_th∈[-1,-0.5,0,0.5] **네 칸 4/4 견고**
  (최대 +146%, 4년합계). **LINK가 이제 Connors RSI/CMO/Elder Ray 3개 지표로 삼중 확인됨** — 지금까지
  가장 신뢰도 높은 단일 코인. 파일: elder_ray_backtest.py
  - BNB 도 초기엔 4/4(롱온리+롱숏 둘다) 나왔으나, 격자 확인 결과 고립된 1칸뿐 → 우연으로 판단, 기각

| Vortex Indicator (VI+/VI- 극단값+되돌림) | 4/4 없음, LINK 3/4(+36%)가 최선, 대부분 마이너스 | 기각 |

## ⭐⭐⭐ 신규 확정 후보 추가 (매우 중요)
- **Chaikin Oscillator(z-score정규화) 롱온리 — LINK** buy_th∈[-2.5,-2.0,-1.5] × exit_th∈[-0.5,0]
  **6칸 전부 4/4, 매우 견고**(최대 +74%). **LINK가 이제 Connors RSI/CMO/Elder Ray/Chaikin 4개 지표로
  사중 확인됨 — 압도적으로 가장 신뢰도 높은 코인.**
- **BTC** buy_th≈-1.0 부근에 4/4 여러개(★6개, 산발적이나 클러스터 있음, 최대 +107%) —
  **이번 세션 전체에서 BTC가 처음으로 4/4 통과.** LINK만큼 깔끔친 않아 '중간신뢰도'로 분류, 추가검증 여지.
- SOL: 고립된 3칸뿐 + 수익률 극단적(+249~396%, 단일거래 의존 의심) → 기각
  파일: chaikin_osc_backtest.py

| Klinger Volume Oscillator(z-score) | LINK 2칸 인접(+107~178%), BNB 3칸 L자(+55~95%), BTC 고립 1칸 | 단독 확정 기준 미달, 보류(참고용) |

| Detrended Price Oscillator (DPO) | 4/4 없음, DOT/BNB 3/4가 최선이나 수익 미미(~0~25%) | 명확히 기각 |

## 🏆 최우수 발견 — Keltner Channel %K (ATR 기반, 극단값+되돌림)
**이번 /loop 세션 전체에서 가장 견고한 결과.** 기본 파라미터(buy=0.1,exit=0.5)만으로 DOT/LINK/SOL 3개
코인이 즉시 4/4 통과 — 다른 지표들처럼 재보정 필요 없이 바로 강한 신호.

- **DOT 롱온리: buy_th=0.05 행 전체(exit 0.3~0.7 다섯 칸) 100% 4/4** ★★★★★
  (최대 +171%). buy=0.0/0.1 행도 대부분 4/4 — 이번 세션 전체에서 가장 넓고 견고한 블록.
- **DOT 롱숏대칭: 거의 전 구간이 3~4/4** (실패 없음에 가까움), 최대 +341% (buy=0.05,exit=0.6)
- **LINK 롱온리**: exit_th=0.5~0.7 부근 클러스터 6칸 4/4 (최대 +120%) — Connors RSI/CMO/Elder Ray/
  Chaikin 에 이어 **5번째 지표로 LINK 재확인**
- **SOL 롱온리**: exit_th=0.5~0.6 클러스터 4칸 4/4 (최대 +112%) — SOL 최초의 신뢰할 만한 통과
- LTC: buy=0.1,exit=0.3/0.4 2칸 인접 — 약한 2차 후보
파일: keltner_backtest.py

| Awesome Oscillator (%AO) | LINK 격자전체가 균일하게 3/4(한 해 항상마이너스), BNB 2~3/4 | 기각 |

| Balance of Power (BOP) | 수익률 거의 0%대, 4/4 없음 | 명확히 기각 |

| Parabolic SAR | 4/4 없음, 대부분 마이너스(-50~-98%) | SuperTrend+ADX 와 동일 실패 패턴 |

## ⭐ 설계 원칙 추가
**"순수 추세추종형 스톱앤리버스 시스템"(SuperTrend, Parabolic SAR)은 반복적으로 실패한다.**
반면 "극단값 도달 후 되돌림"(Connors RSI/CMO/TSI/Elder Ray/Chaikin/Keltner)은 상대적으로 잘 통함.
→ 앞으로도 평균회귀형 극단값+되돌림 방식 위주로 계속 시도.

| 가격 자체의 롤링 Z-score(대조군, N=20) | DOT 기본값에서 4/4 나왔으나 격자확인시 고립 1칸뿐(우연) | 단독 확정 기준 미달 |

## ⭐ 메타 관찰
**DOT는 어떤 지표를 쓰든(정교한 오실레이터든 순수 가격 z-score든) 거의 항상 3~4/4를 기록.**
→ DOT 자체가 이 4년 구간에서 유난히 평균회귀 성향이 강한 자산이라는 뜻. 반면 LINK 는
정교한 지표 구성(Connors/CMO/Elder Ray/Chaikin/Keltner)에서만 견고하고, 단순 z-score론 3/4 그침
→ LINK의 우위는 '평균회귀' 자체보다 특정 계산방식에 더 의존적.

## 🏆🏆 최우수 발견 #2 — Volume Profile POC (거래량 분포 기반, 지표 아닌 시장구조 접근)
**Keltner Channel 다음으로 이번 세션 최고 견고성.** 최근 200봉 가격구간을 20개 구간으로
나눠 거래량이 가장 몰린 가격대(POC)를 찾고, 현재가의 POC대비 괴리%로 신호 생성.

- **LTC 롱온리: buy_th=-2, -3 두 행 전체(8칸) 100% 4/4** ★★★★★★★★ (최대 +208%!!)
  — 이번 세션 통틀어 가장 넓고 견고한 블록. LTC가 이제 Connors RSI에 이어 확실히 이중 확인.
- **DOT 롱온리: buy_th=-5 행 전체(4칸) 4/4 + buy=-3 도 3/4★** (최대 +69%) — 매우 견고
- **ETH 롱숏대칭: buy_th=-2 부근 3칸 클러스터** (최대 +138%) — **ETH 이번 세션 최초 신뢰가능 통과**
파일: volprofile_backtest.py

## ⭐⭐ 신규 확정 후보 추가
- **OBV(가장 단순한 방향성거래량, z-score) 롱온리 — SOL** buy_th=-2.0 행 전체(4칸) 100% 4/4
  (+buy=-1.5 2칸 추가), 최대 +79%. **SOL이 Keltner Channel에 이어 2번째 지표로 재확인.**
  LTC 는 3/4 근접(격자 대부분 3/4, 견고하나 4/4 미달)하나 참고할만함.
  파일: obv_backtest.py

## ⭐⭐ 신규 확정 후보 추가
- **Ichimoku 구름중심 괴리% 롱숏대칭 — ETH** buy_th=-6 행 전체(4칸) 100% 4/4 (최대 +41%)
  + 인접셀 다수. **ETH가 Volume Profile POC에 이어 2번째 지표로 견고하게 재확인.**
- XRP 롱온리: buy_th=-5 부근 4칸 클러스터(최대 +51%), 4개 연도 고르게 플러스(단일해 몰빵 아님)
  — 과거 XRP 거짓양성 이력 때문에 '중간신뢰도·참고용'으로만 분류(완전확정 아님)
  파일: ichimoku_backtest.py

| Schaff Trend Cycle (STC) | 4/4 없음, BTC 전체격자 항상 3/4(한 해 불변 마이너스) | 기각 |

| RSI 다이버전스(가격vsRSI 고점/저점 불일치) | 4/4 없음, 거의 전코인 마이너스 | 기각 |

## ⭐⭐ 신규 확정 후보 추가
- **HMA(Hull이동평균) 괴리% 롱온리 — DOT/LINK 재확인(둘다 4/4), BNB 신규 확정 가능**
  BNB: buy_th=-3,-2 부근 5칸 클러스터(최대 +213%) — 이전 여러 지표(Elder Ray/UO/Klinger)에서
  계속 고립1칸으로 아깝게 탈락했던 BNB가 드디어 credible한 클러스터 확보.
  파일: hma_backtest.py

## 🏆🏆🏆 최우수 발견 #3 — Coppock Curve (장기모멘텀, ROC 두 기간 결합)
**BTC·ETH가 이번 세션 최초로 진짜 견고하게 확정됨** — 지금까지 가장 뚫기 어려웠던 두 대형코인.

- **BTC 롱숏대칭: buy_th=-12 행 전체(5칸) 100% 4/4**, buy=-10/-8도 각 4/5 — 13개+ 칸의 넓은 블록
  (역대 BTC 최고 견고성, 이전 Chaikin의 산발적 클러스터보다 훨씬 강함)
- **ETH 롱숏대칭: buy_th=-6 행 전체(5칸) 100% 4/4, 최대 +167%**, buy=-12/-10/-8도 각 4/5
  (역대 ETH 최고 견고성)
- 이걸로 **테스트한 9개 코인 전부가 최소 1개 이상 견고한 지표 확보 완료**
파일: coppock_backtest.py

| Choppiness Index 필터 + Connors RSI | DOT(4/4→2/4), LINK(4/4→1/4) 오히려 악화. BTC/ETH 개선 미미 | 필터 결합 재확인: 해롭다 |

## ⭐⭐⭐ 신규 확정 후보 추가 (중요 — ETC 2중 확인 달성)
- **PPO(%MACD) 롱숏대칭 — ETC buy_th=-2 행 전체(5칸) 100% 4/4** (최대 +36%)
  **ETC가 드디어 Connors RSI에 이어 2번째 지표로 재확인됨** (그동안 ETC는 단일지표뿐이었음)
- **ETH buy_th=-2 행 전체(5칸) 100% 4/4** (최대 +35%) — ETH의 4번째 확인지표
- **SOL buy_th=-2 부근 4칸 클러스터** (최대 +42%) — SOL의 3번째 확인지표
  (BTC/BNB는 이 임계값에서 거래 자체가 안 나옴 — buy_th 재조정 여지는 있으나 낮은 우선순위)
파일: ppo_backtest.py

| NVI(스마트머니 이론, 거래량감소일만 누적) 롱온리 — BTC | buy=-0.5 행 전체(4칸) 4/4 (최대+94%), buy=-1.0도 3칸 — **BTC 3번째 확인지표.** ETH는 고립3칸(기각) |

| TRIX(3중평활 모멘텀) 롱숏 — ETC | buy=-0.2,-0.15 부근 3칸 클러스터(최대+66%) — **ETC 3번째 확인지표.** BNB는 고립1칸(기각) |

| Kaufman Efficiency Ratio | 최악급 기각, 대부분 -70~98%, 4/4 없음 | '저효율=스냅백' 가설 반증 |

| Volatility RSI(Dorsey) | 4/4 없음, 수익률 미미(대부분 ±10%이내) | 기각 |

| Stochastic RSI | 4/4 없음, LINK 3/4가 최선, 대부분 마이너스 | 기각 |

| Ehlers COG(재구현, z-score) 롱온리 — LINK | buy=-2.0,-1.5 부근 6칸 클러스터(최대+208%) — **LINK 6번째+ 확인지표**. 원래 버전은 버그였으나 z-score 정규화로 수정 후 재검증 성공 | 확정(LINK 한정) |

| Relative Volatility Index(Dorsey, span평활 재구현) | buy_th 15~40 전 구간에서 9코인 전부 4/4 없음 (대부분 ±5%p 이내 미미한 손익) | **기존 vol_rsi_backtest.py(루프20회차)와 동일 지표였음** — 이름만 보고 다른 지표로 착각해 중복 검증. 평활방식만 다름(span=14 vs Wilder alpha=1/14)이라 결론 동일하게 재확인, 파일은 중복이라 미보관 |

## ⭐ 신규 확정 (루프 24회차)
- **Elder's Force Index(EFI, z-score) 롱온리** — "가격변화×거래량"을 직접 곱하는 방식으로
  OBV/Chaikin/Klinger와 메커니즘이 다름. 롱숏대칭은 롱온리보다 전부 나빠서 기각, 롱온리만 채택.
  - **DOT: exit=0.0에서 buy −1.25~−2.00 4칸 연속 4/4** (견고) — 최대 buy=−1.25 exit=0.0 → +81%
  - **ETC: exit=0.0에서 buy −1.00~−1.50 3칸 연속 4/4** (견고) — 최대 buy=−1.00 exit=0.0 → +120%
  - LINK/SOL/BNB: 격자탐색 전 구간 3/4가 최선 → 미확정
파일: strategies/confirmed/force_index_backtest.py

## ⭐ 신규 확정 (루프 25회차)
- **Percentage Volume Oscillator(PVO) 롱온리** — PPO를 거래량에 적용(가격 방향 전혀 안 봄, 순수 거래량 모멘텀). 롱숏대칭은 거의 전 코인 마이너스라 기각.
  - **SOL: buy=-24 행이 exit −10~+10 5칸 전부 4/4** (역대급 견고) — 최대 buy=-24,exit=+10 → +130.1%(95건, 승률58%)
  - **ETH: exit=+10 열이 buy −26~−32 4칸 전부 4/4** (견고) — 최대 buy=-28,exit=+10 → +74.6%(102건, 승률59%)
  - LTC는 buy=-32 단일셀만 4/4(양옆 -30/-34는 2/4) → **고립셀=우연 판정, 미확정**
  - DOT/LINK/XRP/ETC/BTC/BNB: 3/4가 최선 → 미확정
파일: strategies/confirmed/pvo_backtest.py

## 다음 시도 후보
- (새 카테고리 계속 탐색 — "RVI/Volatility RSI" 계열은 이미 소진, 이름 유사한 지표 재확인 전 vol_rsi_backtest.py·rvi_backtest.py 먼저 대조할 것)
