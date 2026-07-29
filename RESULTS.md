# 크립토 자동매매 전략 검증 리포트

**기간**: 2026-07-28 ~ 2026-07-30 (약 2일간)
**방법론**: 1시간봉, 4년치 데이터(2022-07~2026-07)를 4개 연도 구간(하락/횡보/강세 혼재)으로 나눠
**전 구간에서 플러스(4/4)** 인 (지표, 코인) 조합만 "확정"으로 인정. 수수료 왕복 0.08% 반영,
파라미터 격자 탐색으로 견고성(우연 아님) 확인. 총 **30개 이상의 지표/전략**을 검증.

## 왜 이렇게 엄격한 기준을 썼나

프로젝트 초반에 MA 교차, RSI 평균회귀 등 단순 전략들이 전부 손실이었고, 심지어 "그럴듯해 보이는"
신호(예: BTC·XRP 우연 통과)도 여러 코인·여러 기간으로 넓혀보면 **통계적 우연 범위**에 불과했다는 걸
반복해서 확인했다. 그래서:
- 반드시 **train/test 또는 4개 연도 구간 전부**에서 검증
- 반드시 **파라미터 격자(견고성 검사)** 로 "우연히 걸린 셀 하나"가 아닌지 확인
- 반드시 **여러 코인**으로 넓혀 다중검정 함정을 피함

---

## ✅ 확정된 전략 (코인별 교차검증 지표 수)

| 코인 | 확정 지표 수 | 대표 지표(가장 견고) | 대표 결과 |
|---|---|---|---|
| **LINK** | 6개+ | Chaikin Oscillator | 4년 +74~208% |
| **DOT** | 4개+ | Keltner Channel %K | 4년 +171% |
| **ETH** | 4개 | Coppock Curve | 4년 +167% |
| **BTC** | 3개 | Coppock Curve | 4년 최대 +107%(다수 셀) |
| **ETC** | 3개 | Connors RSI / PPO / TRIX | 4년 +36~66% |
| **SOL** | 3개 | Keltner Channel / OBV | 4년 +79~112% |
| **LTC** | 2개 | Volume Profile POC | 4년 **+208%** (8칸 전체 4/4) |
| **BNB** | 1개 | HMA 괴리% | 4년 +213%(5칸 클러스터) |
| **XRP** | 1개(중간신뢰도) | Ichimoku 구름괴리 | 4개 연도 고르게 플러스, 단 과거 거짓양성 이력으로 신중 필요 |

**핵심**: 9개 코인 전부 최소 1개 이상의 견고한 지표로 확정됨. 가장 신뢰도 높은 건 **LINK**(6개+
서로 다른 지표 계열에서 재확인)와 **DOT**.

### 최초 확정 전략 (베이스라인)
**Connors RSI 롱숏대칭** (RSI(3)+연속상승일수+ROC순위 합성, buy_th=10, exit_th=50, MA200 추세필터)
— DOT/LINK/ETC 전부 4/4 통과. 파일: `strategies/connors_rsi_ls.py`

### 이후 발견된 주요 확정 지표 (파일명)
| 지표 | 확정 코인 | 파일 |
|---|---|---|
| CMO (평활화 없는 모멘텀) | LINK, XRP(중간) | `cmo_backtest.py` |
| TSI (이중평활 모멘텀) | DOT | `tsi_backtest.py` |
| Elder Ray (추세EMA 괴리) | LINK | `elder_ray_backtest.py` |
| Chaikin Oscillator (거래량) | LINK, BTC(중간) | `chaikin_osc_backtest.py` |
| **Keltner Channel %K** 🏆 | DOT, LINK, SOL | `keltner_backtest.py` |
| **Volume Profile POC** 🏆 | LTC, DOT, ETH(중간) | `volprofile_backtest.py` |
| OBV (단순 방향성거래량) | SOL | `obv_backtest.py` |
| Ichimoku 구름괴리 | ETH, XRP(중간) | `ichimoku_backtest.py` |
| HMA(Hull이동평균) 괴리 | DOT, LINK, BNB | `hma_backtest.py` |
| **Coppock Curve** 🏆 | BTC, ETH | `coppock_backtest.py` |
| PPO (%MACD) | ETC, ETH, SOL | `ppo_backtest.py` |
| NVI (스마트머니 거래량) | BTC | `nvi_backtest.py` |
| TRIX (3중평활 모멘텀) | ETC | `trix_backtest.py` |
| Ehlers COG (무게중심) | LINK | `cog_backtest.py` |

🏆 = 이번 검증에서 가장 넓고 견고한 블록을 보인 "최우수 발견"

---

## ⭐ 발견한 설계 원칙 (일반화 가능한 통찰)

1. **"극단값 도달 후 되돌림" 방식이 "자기 자신의 평활선과 교차" 방식보다 압도적으로 낫다.**
   Fisher Transform, RVI(신호선 크로스)는 과매매(휩쏘)로 승률 30~40%대에 그쳐 실패.
   Connors RSI, CMO, Keltner 등은 임계값+되돌림 방식으로 훨씬 견고했다.

2. **"순수 추세추종형 스톱앤리버스"(SuperTrend, Parabolic SAR)는 반복적으로 실패한다.**
   이 시간대·자산군에서는 평균회귀형 접근이 추세추종보다 우위.

3. **신호 조합(AND/OR)은 오히려 해롭다.** 좋은 단일 지표에 다른 지표나 필터(삼각수렴, Choppiness
   Index 등)를 덧붙이면 거의 항상 성과가 나빠졌다. 좋은 신호를 필터로 "정제"하려다 오히려 훼손함.

4. **파라미터 견고성 검사가 필수.** 격자 전체에서 고립된 셀 1~2개만 통과하면 우연(과최적화)일 가능성이
   크다. 여러 파라미터에 걸쳐 넓은 블록으로 통과해야 신뢰 가능 (예: BNB·ATOM·BCH는 이 기준으로 여러 번
   탈락, LINK·DOT·LTC는 넓은 블록으로 반복 확정).

5. **다중검정(multiple testing)을 항상 의심하라.** 14개 코인 중 우연히 1~2개만 통과하는 결과는
   통계적 기대값과 일치하는 경우가 많았다(우연). 여러 코인·여러 기간으로 넓혀야 진짜와 우연을 가른다.

6. **재보정(calibration)을 반드시 확인.** Ultimate Oscillator, COG 등은 초기 임계값이 잘못 잡혀
   거래가 0건이거나 버그로 왜곡된 결과가 나왔다. 지표별 실제 값 분포를 먼저 확인해야 한다.

7. **XRP처럼 특정 한 해(이벤트성 폭등)에 몰빵된 결과는 착시일 확률이 높다.** 4개 연도에 고르게
   분산된 수익인지 반드시 확인.

---

## ❌ 기각된 지표 (30개 이상 검증)

MA교차, RSI(2)평균회귀, MACD신호, SuperTrend+ADX, Full Crypto Pack, 삼각수렴, 이중바닥/천장,
깃발형, Ehlers Fisher Transform, Ehlers Laguerre RSI, Aroon, RVI, MFI, Ultimate Oscillator,
Williams %R, Vortex Indicator, Klinger(단독기준 미달), DPO, Awesome Oscillator, Balance of
Power, Parabolic SAR, 가격 Z-score(대조군), Schaff Trend Cycle, RSI 다이버전스, Choppiness
필터, Kaufman Efficiency Ratio, Volatility RSI, Stochastic RSI

전체 상세 로그: [`strategies/loop_log.md`](strategies/loop_log.md)

---

## ⚠️ 중요한 한계와 주의사항

- **백테스트이지, 실전 검증이 아님.** 슬리피지는 반영 안 됨(수수료만 반영). 실제 체결가는 이보다 나쁠 수 있음.
- **2022-07~2026-07 특정 4년 구간의 결과.** 다른 시기·다른 시장 국면에서 재현된다는 보장은 없음.
- **다중검정 위험은 이 리포트 자체에도 적용됨.** 30개 이상의 지표를 테스트했으니, 그중 일부의
  "확정"도 순전히 우연일 가능성을 완전히 배제할 수 없다. 실전 투입 전 반드시 페이퍼 트레이딩으로
  추가 검증 필요.
- 실제 자금 투입 전 **소액·페이퍼 트레이딩부터** 시작할 것을 권장.

---

## 다음 단계 제안
1. 확정된 지표들(특히 LINK/DOT)을 조합해 페이퍼 트레이딩 봇으로 구현
2. 5년 이상 더 긴 기간 또는 다른 시장 국면으로 추가 검증
3. 실거래소(바이낸스) 테스트넷에서 실시간 페이퍼 트레이딩 시작
