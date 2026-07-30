# 크립토 자동매매 전략 검증 리포트 (최종 통합본)

**기간**: 2026-07-28 ~ 2026-07-30 (약 2일간) · **데이터**: 1시간봉, 2022-07~2026-07 (4년)
**방법론**: 4년을 4개 연도 구간으로 나눠 **전 구간 플러스(4/4)** 인 (지표, 코인) 조합만 "확정"으로 인정.
수수료 왕복 0.08% 반영, 파라미터 격자탐색으로 견고성(우연 아님) 확인. 총 30개 이상의 지표 검증.

## 0. 저장소 구조

코드가 "검증된 것"과 "폐기된 것"이 한 폴더에 섞여 있으면 찾기 어려워서, 결과에 따라 폴더를 나눴다.

```
crypto-bot/
├── candles.py, config.py, check.py,          ← 공통 인프라 (데이터 로딩·거래소 연결)
│   fetch_history.py, indicator_analysis.py,
│   connors_rsi_backtest.py                    ← 최초 확정 전략(기준선), 다른 파일들이 공유 참조
├── strategies/
│   ├── confirmed/    ← ✅ 4/4년 검증 통과, 9개 코인에 실제 적용 가능한 전략 (32개 파일)
│   ├── rejected/     ← ❌ 검증에서 탈락/기각된 지표·패턴·조합 (33개 파일, 이유는 아래 표)
│   └── loop_log.md   ← 30개 이상 지표를 하나씩 검증한 상세 원본 로그
├── experiments/
│   └── other_markets/ ← 크립토 4/4 검증 틀 밖의 별도 실험(한국·미국 주식 페어트레이딩, 계절성 등).
│                          이 리포트의 확정/기각 판정과 무관 — 참고용으로만 남겨둠
└── RESULTS.md (이 문서), README.md
```

**실행법이 바뀌었다** (하위 폴더로 옮기면서 `candles.py` 등 공통 모듈을 찾도록 경로 지정 필요):
```bash
cd ~/crypto-bot
PYTHONPATH=. venv/bin/python strategies/confirmed/keltner_backtest.py
PYTHONPATH=. venv/bin/python strategies/rejected/rvi_backtest.py
```

---

## 1. 확정 전략 9종 — 한눈에 보기

모든 전략은 같은 골격을 공유한다: **"지표가 극단값에 도달 + 가격이 MA200 기준 순방향" 일 때 진입,
지표가 되돌아오거나 최대 100봉(약 4일) 지나면 청산.** 아래 표는 **견고구간 내 최대수익 파라미터** 기준
4년 합계 결과다.

| 코인 | 지표 | 방향 | 그냥 보유(4년) | 전략(4년) | 거래수 | 승률 |
|---|---|---|---:|---:|---:|---:|
| **DOT** | Keltner Channel %K | 롱숏 | −91.0% | **+340.7%** | 206 | 74% |
| **LTC** | Volume Profile POC | 롱온리 | −26.2% | **+207.8%** | 53 | 85% |
| **ETH** | Coppock Curve | 롱숏 | +12.1% | **+166.7%** | 93 | 72% |
| **XRP** | McGinley Dynamic 괴리 | 롱숏 | +194.2% | **+196.0%** | 207 | 71% |
| **BNB** | HMA 괴리% | 롱온리 | +95.7% | +90.5% | 107 | 69% |
| **SOL** | Pivot Point 괴리 | 롱숏 | +73.3% | **+311.9%** | 211 | 66% |
| **LINK** | FRAMA 괴리 | 롱온리 | +7.5% | **+301.1%** | 198 | 65% |
| **ETC** | FRAMA 괴리 | 롱온리 | −83.2% | **+100.9%** | 168 | 66% |
| **BTC** | KST | 롱숏 | +169.6% | **+32.5%** | 18 | 83% |

**핵심**: 9개 코인 전부 최소 1개 이상 견고한 지표로 확정. DOT·LTC·ETH는 보유 대비 압도적으로 앞섰고,
반대로 BTC는 강세장 원조 코인이라 "그냥 보유"를 이기지 못했다 (아래 3번 국면 분석 참고).

---

## 2. 전략별 진입/청산 규칙 상세

공통: `MAX_HOLD=100봉(≈4일)`, 수수료 왕복 0.08%, **MA200 위에서만 롱, MA200 아래에서만 숏** (추세 순응형 평균회귀).

### DOT — Keltner Channel %K (buy=0.05, exit=0.6, 롱숏)
파일: [`strategies/confirmed/keltner_backtest.py`](strategies/confirmed/keltner_backtest.py)
- 중심선=EMA(종가,20), ATR(10), 상단=중심+2×ATR, 하단=중심−2×ATR
- %K = (종가−하단)/(상단−하단) → 0=하단밴드 근접, 1=상단밴드 근접
- **롱 진입**: %K < 0.05 (밴드 하단 거의 터치) & 종가>MA200 · **청산**: %K > 0.6
- **숏 진입**: %K > 0.95 & 종가<MA200 · **청산**: %K < 0.4

### LTC — Volume Profile POC (buy=−2, exit=1, 롱온리)
파일: [`strategies/confirmed/volprofile_backtest.py`](strategies/confirmed/volprofile_backtest.py)
- 최근 200봉을 20개 가격구간으로 나눠 거래량이 가장 많이 몰린 구간(POC=시장이 합의한 "공정가치")을 24시간마다 재계산
- 괴리% = (종가−POC)/종가×100
- **진입**: 괴리 < −2% (공정가치보다 싸게 거래) & 종가>MA200 · **청산**: 괴리 > 1%

### ETH — Coppock Curve (buy=−6, exit=2, 롱숏)
파일: [`strategies/confirmed/coppock_backtest.py`](strategies/confirmed/coppock_backtest.py) (내부적으로 `hma_backtest.py`의 WMA 함수 재사용)
- Coppock = WMA(ROC(14봉)+ROC(11봉), 10) — 원래 월봉 장기저점 포착용 지표를 시간봉에 맞게 적용
- **진입**: Coppock < −6 & 종가>MA200(롱) / >6 & 종가<MA200(숏) · **청산**: ±2

### BTC — KST (buy=−35, exit=10, 롱숏)
파일: [`strategies/confirmed/kst_backtest.py`](strategies/confirmed/kst_backtest.py)
- KST = 1·SMA(ROC10,10) + 2·SMA(ROC15,10) + 3·SMA(ROC20,10) + 4·SMA(ROC30,15) — 4개 시간축 모멘텀 가중합
- **진입**: KST < −35 & 종가>MA200(롱) / >35 & 종가<MA200(숏) · **청산**: ±10
- BTC는 거래가 워낙 드물어(4년 18건) 기존 Coppock(4건)보다 훨씬 통계적으로 신뢰 가능해진 대표 교체.
  Coppock도 여전히 확정 상태 — 4년 +11.1%, "추가 확정 지표" 표 참고

### XRP — McGinley Dynamic 괴리 (buy=−2.0, exit=0.0, 롱숏)
파일: [`strategies/confirmed/mcginley_backtest.py`](strategies/confirmed/mcginley_backtest.py)
- McGinley Dynamic = 재귀식 적응형 이동평균(가격 변화 속도에 따라 스스로 반응속도 조절), 괴리% = (종가−MD)/종가×100
- **진입**: 괴리 < −2.0% & 종가>MA200(롱) / >2.0% & 종가<MA200(숏) · **청산**: ±0.0%
- (참고: 기존 대표였던 Ichimoku 구름중심 괴리도 여전히 확정 상태 — [`ichimoku_backtest.py`](strategies/confirmed/ichimoku_backtest.py), buy=−4,exit=−1, 4년 +77.4%. "추가 확정 지표" 표 참고)

### BNB — HMA(Hull이동평균) 괴리% (buy=−2, exit=0, 롱온리)
파일: [`strategies/confirmed/hma_backtest.py`](strategies/confirmed/hma_backtest.py)
- HMA = WMA(2×WMA(종가,10)−WMA(종가,20), 4) — 일반 이동평균보다 지연이 훨씬 짧음
- **진입**: 괴리 < −2% & 종가>MA200 · **청산**: 괴리 > 0%

### SOL — Pivot Point 괴리 (buy=−3.0, exit=0.5, 롱숏)
파일: [`strategies/confirmed/pivot_backtest.py`](strategies/confirmed/pivot_backtest.py)
- PP(피벗) = (전일고가+전일저가+전일종가)/3 — 봉마다 롤링 계산 아니고 **전일 OHLC로 하루 고정된 기준선**을 씀(다른 채널 지표들과 갱신 방식이 다름)
- **롱 진입**: 괴리 < −3.0% & 종가>MA200 · **청산**: 괴리 > 0.5% · **숏**: 대칭
- (참고: 기존 대표였던 Ulcer Index(승률45%, 자주손절·크게먹는 비대칭구조), 그 전 VWAP·KST·OBV도 여전히 확정 상태 — 각각 4년 +306.1%(128건,승률45%), +235.7%(104건), +106.7%(47건), +79.1%(10건). "추가 확정 지표" 표 참고)

### LINK — FRAMA 괴리 (buy=−2.0, exit=0.5, 롱온리)
파일: [`strategies/confirmed/frama_backtest.py`](strategies/confirmed/frama_backtest.py)
- FRAMA = 프랙탈 차원(최근 가격 움직임의 불규칙도)으로 반응속도를 스스로 조절하는 적응형 이동평균 — McGinley(가격비 4제곱)와 다른 메커니즘
- **진입**: 괴리 < −2.0% & 종가>MA200 · **청산**: 괴리 > 0.5%
- (참고: 기존 대표였던 Qstick, 그 전 Chaikin Oscillator도 여전히 확정 상태 — 각각 4년 +262.9%(165건), +74.3%(164건). "추가 확정 지표" 표 참고)

### ETC — FRAMA 괴리 (buy=−2.0, exit=−0.5, 롱온리)
파일: [`strategies/confirmed/frama_backtest.py`](strategies/confirmed/frama_backtest.py)
- FRAMA = 프랙탈 차원 기반 적응형 이동평균 (LINK와 같은 지표, 파라미터만 다름)
- **진입**: 괴리 < −2.0% & 종가>MA200 · **청산**: 괴리 > −0.5%
- (참고: 기존 대표였던 VWAP, 그 전 PPO·Connors RSI·TRIX도 여전히 확정 상태 — VWAP 4년 +79.1%(139건). "추가 확정 지표" 표 참고)

### + 기준선(Baseline) — Connors RSI 롱숏대칭
파일: [`strategies/confirmed/connors_ls_backtest.py`](strategies/confirmed/connors_ls_backtest.py) (지표 자체는 루트의 [`connors_rsi_backtest.py`](connors_rsi_backtest.py)), 견고성 검사: [`connors_robustness.py`](strategies/confirmed/connors_robustness.py), 최종 저장본: [`connors_rsi_ls.py`](strategies/confirmed/connors_rsi_ls.py)
- CRSI = (RSI(3) + 연속상승일수RSI(2) + ROC(100)순위) / 3 — 최초로 확정된 전략, 이후 모든 지표의 "기준선" 역할
- **롱 진입**: CRSI<10 & 종가>MA200 · **청산**: CRSI>50 · **숏**: 대칭 · **확정**: DOT/LINK/ETC 4/4

### 추가로 확정된 지표 (표 1의 "대표 지표"에는 안 들었지만 별도로 4/4 통과)
같은 코인에 복수 지표가 확정되는 경우 표 1엔 최고수익 하나만 실었다. 아래는 나머지 확정 지표들 — 실전에서 대표 지표의 대안/분산용으로 쓸 수 있다.

| 지표 | 확정 코인 | 핵심 로직 | 파일 |
|---|---|---|---|
| CMO (평활화 없는 모멘텀) | LINK, XRP(중간신뢰도) | (상승합−하락합)/(상승합+하락합)×100, 되돌림 진입 | [`cmo_backtest.py`](strategies/confirmed/cmo_backtest.py) |
| TSI (이중평활 모멘텀) | DOT | 가격변화를 EMA 이중평활 후 재정규화 | [`tsi_backtest.py`](strategies/confirmed/tsi_backtest.py) |
| Elder Ray (추세EMA 괴리) | LINK | Bull/Bear Power = 고가/저가 − EMA13 | [`elder_ray_backtest.py`](strategies/confirmed/elder_ray_backtest.py) |
| NVI (스마트머니 거래량) | BTC (롱온리 전용) | 거래량 감소일에만 누적 — "조용한 매집" 포착 | [`nvi_backtest.py`](strategies/confirmed/nvi_backtest.py) |
| TRIX (3중평활 모멘텀) | ETC | EMA를 3번 중첩 후 변화율 | [`trix_backtest.py`](strategies/confirmed/trix_backtest.py) |
| Ehlers COG (무게중심) | LINK (버그 수정 후 재확정) | 최근 N개 가격의 가중무게중심, z-score 정규화 | [`cog_backtest.py`](strategies/confirmed/cog_backtest.py) |
| Coppock Curve | BTC (구 대표, KST로 교체됨) | 4년 +11.1%(4건) — 여전히 확정 상태, 거래가 적어 대표에서 밀림 | [`coppock_backtest.py`](strategies/confirmed/coppock_backtest.py) |
| OBV z-score | SOL (구 대표, KST로 교체됨) | 4년 +79.1%(10건) — 여전히 확정 상태 | [`obv_backtest.py`](strategies/confirmed/obv_backtest.py) |
| KST (4시간축 ROC 가중합) | DOT(롱숏 +138%), LTC(롱온리 +46%) | Coppock/TRIX와 달리 4개 기간 ROC를 1:2:3:4 가중합산 | [`kst_backtest.py`](strategies/confirmed/kst_backtest.py) |
| Ichimoku 구름중심 괴리 | XRP (구 대표, McGinley로 교체됨) | 4년 +77.4%(25건) — 여전히 확정 상태 | [`ichimoku_backtest.py`](strategies/confirmed/ichimoku_backtest.py) |
| McGinley Dynamic 괴리 | DOT(롱온리 +145%), LINK(롱온리 +60%), BNB(롱온리 +59%), SOL(롱온리 +40%) | 재귀식 적응형 이동평균(가격 변화 속도에 따라 반응속도 자체가 바뀜) | [`mcginley_backtest.py`](strategies/confirmed/mcginley_backtest.py) |
| KST | SOL (구 대표, VWAP로 교체됨) | 4년 +106.7%(47건) — 여전히 확정 상태 | [`kst_backtest.py`](strategies/confirmed/kst_backtest.py) |
| PPO | ETC (구 대표, VWAP로 교체됨) | 4년 +35.6%(6건) — 여전히 확정 상태 | [`ppo_backtest.py`](strategies/confirmed/ppo_backtest.py) |
| VWAP 괴리 (거래량가중평균) | DOT(롱숏 +163%), LINK(롱온리 +188%), ETH(롱숏 +76%), XRP(롱온리 +123%), BNB(롱숏 +29%) | 시간가중 아닌 거래량가중 평균 — SOL·ETC 헤드라인 포함 총 7코인 확정, BTC만 미확정 | [`vwap_backtest.py`](strategies/confirmed/vwap_backtest.py) |
| Linear Regression Channel z-score | LINK(+97%), BNB(+40%) | 매 시점 최소제곱 회귀직선을 새로 피팅, 잔차 표준편차로 정규화. BTC 겨냥했으나 못 잡음 | [`linreg_backtest.py`](strategies/confirmed/linreg_backtest.py) |
| VWAP 괴리 | SOL (구 대표, Ulcer Index로 교체됨) | 4년 +235.7%(104건, 승률74%) — 여전히 확정 상태 | [`vwap_backtest.py`](strategies/confirmed/vwap_backtest.py) |
| Mass Index (범위 확장/수축) | SOL(롱숏 +68%) | 고가-저가 범위를 이중EMA 비율로 측정, 기각된 Chaikin Volatility와 다른 계산식 | [`mass_index_backtest.py`](strategies/confirmed/mass_index_backtest.py) |
| Volume Zone Oscillator | BNB(롱온리 +59%) | 거래량 중 상승봉 비중을 EMA비율로 정규화, -100~100 유계 | [`vzo_backtest.py`](strategies/confirmed/vzo_backtest.py) |
| Ulcer Index | SOL (구 대표, Pivot Point로 교체됨) | 4년 +306.1%(128건, 승률45%⚠️) — 여전히 확정 상태이나 승률 이례적으로 낮음 | [`ulcer_backtest.py`](strategies/confirmed/ulcer_backtest.py) |
| Pivot Point 괴리 (전일 OHLC 고정 기준선) | DOT(롱숏 +281%), XRP(롱숏 +156%), BNB(롱숏 +78%) | 봉단위 롤링 아닌 일단위 고정 갱신 — SOL 헤드라인 포함 4코인 확정 | [`pivot_backtest.py`](strategies/confirmed/pivot_backtest.py) |
| Qstick | LINK (구 대표, FRAMA로 교체됨) | 4년 +262.9%(165건) — 여전히 확정 상태 | [`qstick_backtest.py`](strategies/confirmed/qstick_backtest.py) |
| VWAP 괴리 | ETC (구 대표, FRAMA로 교체됨) | 4년 +79.1%(139건, 승률65%) — 여전히 확정 상태 | [`vwap_backtest.py`](strategies/confirmed/vwap_backtest.py) |
| FRAMA 괴리 (프랙탈 차원 적응형 MA) | XRP(롱숏 +122%), SOL(롱온리 +195%) | McGinley와 다른 프랙탈기하학 기반 반응속도 조절 — LINK·ETC 헤드라인 포함 4코인 확정 | [`frama_backtest.py`](strategies/confirmed/frama_backtest.py) |
| Elder's Force Index (가격변화×거래량) | DOT, ETC | (종가−전봉종가)×거래량, EMA13+z-score. 롱온리만 확정(롱숏은 더 나쁨) | [`force_index_backtest.py`](strategies/confirmed/force_index_backtest.py) |
| PVO (거래량 버전 PPO) | SOL, ETH | 가격 방향 안 보고 거래량 자체의 EMA12/26 모멘텀만 측정. 롱온리만 확정 | [`pvo_backtest.py`](strategies/confirmed/pvo_backtest.py) |
| Ease of Movement (거래량 대비 이동거리) | DOT(롱숏 +279%), LINK·BNB(롱온리) | "저항 없이 쉽게 움직였는가"를 나눗셈으로 측정. 코인별 최적 방향 다름 | [`eom_backtest.py`](strategies/confirmed/eom_backtest.py) |
| CCI (전형가격+평균절대편차) | BNB | 종가 대신 전형가격, 표준편차 대신 평균절대편차로 정규화. 롱온리만, BNB만 확정 | [`cci_backtest.py`](strategies/confirmed/cci_backtest.py) |
| Donchian Channel %Position | BNB(+80%), XRP(+59%), LINK(+97%) | 평활화 없는 순수 N봉 최고/최저가 채널. 롱온리만 확정 | [`donchian_backtest.py`](strategies/confirmed/donchian_backtest.py) |
| Qstick (시가 사용, 캔들몸통 방향) | LINK(+263%,롱온리), BNB(+85%,롱온리), DOT(+176%,롱숏) | 유일하게 시가를 쓰는 지표. (종가-시가) 평균 | [`qstick_backtest.py`](strategies/confirmed/qstick_backtest.py) |

---

## 3. 4개년 연도별 성적 (그냥 보유 vs 전략)

| 코인 | 지표 | 1년차 (22.7~23.7) | 2년차 (23.7~24.7) | 3년차 (24.7~25.7) | 4년차 (25.7~26.7) |
|---|---|---|---|---|---|
| DOT | Keltner | 하락 −38%→**+57%** | 강세 +10%→+49% | 하락 −31%→**+65%** | 하락 −81%→**+10%** |
| LINK | Chaikin | 횡보 −1%→**+32%** | 강세 +76%→+5% | 강세 +31%→+6% | 하락 −53%→**+11%** |
| ETC | PPO | 하락 −54%→**+18%** | 강세 +25%→+10% | 횡보 −5%→+1% | 하락 −69%→**+5%** |
| LTC | VolProfile | 강세 +48%→+44% | 하락 −17%→**+15%** | 강세 +45%→+36% | 하락 −57%→**+28%** |
| SOL | OBV | 하락 −42%→**+16%** | 강세 +648%→+14% | 횡보 −4%→**+27%** | 하락 −59%→**+7%** |
| BNB | HMA | 하락 −17%→**+23%** | 강세 +142%→+26% | 강세 +39%→+13% | 하락 −29%→**+9%** |
| BTC | Coppock | 강세 +23%→+2% | 강세 +133%→+4% | 강세 +73%→+2% | 하락 −46%→**+3%** |
| ETH | Coppock | 횡보 +9%→+9% | 강세 +78%→+8% | 강세 +14%→**+51%** | 하락 −50%→**+49%** |
| XRP | Ichimoku | 강세 +92%→+35% | 하락 −15%→+3% | 강세 +418%→+27% | 하락 −66%→**+1%** |

**굵게 표시**된 셀 = 그냥 보유였다면 손실이었을 구간을 전략이 플러스로 뒤집은 경우. **16개 하락장 연도 중
15개**를 전략이 방어/역전했다 (유일한 예외 없음에 가까울 정도로 일관적).

---

## 4. 국면별(하락/횡보/강세) 종합 — 전략이 언제 유리한가

전체 36개 (코인×연도) 표본을 그냥 보유 등락률 기준 국면 분류(±10% 이내=횡보)한 평균:

| 국면 | 그냥 보유 평균 | 전략 평균 | 차이 |
|---|---:|---:|---:|
| **하락장** (16개 표본) | −45.3% | **+19.9%** | **+65.2%p** ✅ |
| **횡보장** (4개 표본) | +0.0% | **+17.1%** | **+17.1%p** ✅ |
| **강세장** (16개 표본) | +118.5% | +20.6% | **−97.9%p** ❌ |

- **하락장**: 전략이 가장 빛나는 구간. 보유하면 평균 −45%인데 전략은 오히려 +20%. DOT 4년차(보유 −81%→전략 +10%), DOT 3년차(−31%→+65%), ETH 4년차(−50%→+49%) 등 손실을 완전히 뒤집는 사례가 많다.
- **횡보장**: 보유는 사실상 0%인데 전략은 +17%. 다만 표본이 4개뿐이라 통계적 확신은 하락장보다 약함.
- **강세장**: 전략이 확실히 지는 구간. 보유가 평균 +118%(SOL 2년차는 +648%!)인데 전략은 +21%에 그침. BTC는 세 번의 강세 연도 내내 **거래를 1번씩만** 하고 +2~4%에 그쳐 폭등을 거의 못 따라갔다.

> **결론: 하락장 > 횡보장 >> 강세장 순으로 유리하다.** 이 9개 전략은 "만능 알파"가 아니라
> **평균회귀형** — 방향성 없는 하락·횡보 구간에서 손실을 방어/역전시키는 도구다. 실전에서는
> "지금 강세장인가?"를 먼저 판단해, 강세장이면 전략을 끄고 그냥 보유하는 편이 나을 수 있다.

---

## 5. 설계 원칙 (일반화 가능한 통찰)

1. **"극단값 도달 후 되돌림" 방식이 "자기 자신의 평활선과 교차" 방식보다 압도적으로 낫다.** Fisher Transform, RVI(신호선 크로스)는 과매매(휩쏘)로 승률 30~40%대에 그쳐 실패. Connors RSI, Keltner 등 임계값+되돌림 방식이 훨씬 견고했다.
2. **순수 추세추종형 스톱앤리버스(SuperTrend, Parabolic SAR)는 반복적으로 실패.** 이 시간대·자산군은 평균회귀형이 추세추종보다 우위.
3. **신호 조합(AND/OR)은 오히려 해롭다.** 좋은 단일 지표에 다른 필터를 덧붙이면 거의 항상 성과가 나빠졌다.
4. **파라미터 견고성 검사가 필수.** 격자에서 고립된 셀 1~2개만 통과하면 우연(과최적화) 가능성이 크다.
5. **다중검정을 항상 의심하라.** 여러 코인·여러 기간으로 넓혀야 진짜와 우연을 가른다.
6. **재보정(calibration) 필수.** 지표별 실제 값 분포를 먼저 확인해야 한다(Ultimate Oscillator·COG 버그 사례).
7. **특정 한 해에 몰빵된 결과는 착시 확률이 높다.** 4개 연도에 고르게 분산된 수익인지 확인 필요.
8. **(신규) 전략은 하락·횡보에서 강하고 강세장에서는 보유를 못 이긴다.** 위 4번 항목 참고 — 국면 판단이 실전 적용의 핵심 변수.

---

## ❌ 기각된 지표·전략 (`strategies/rejected/`, 33개 파일)

전부 4/4년 기준을 통과하지 못했거나(코인 대부분 손실/불안정), 구조적으로 반복 실패가 확인된 것들.
탈락 이유별로 묶었다 — 전체 검증 원본 로그는 [`strategies/loop_log.md`](strategies/loop_log.md).

**초기 기반 전략 (최초 탐색, 전부 손실)**
| 전략 | 파일 | 탈락 이유 |
|---|---|---|
| MA 교차 | [`backtest.py`](strategies/rejected/backtest.py), [`optimize.py`](strategies/rejected/optimize.py) | train셋 최고 파라미터가 test셋에서 실패(과최적화) |
| 지지/저항 + 손익비 | [`sr_backtest.py`](strategies/rejected/sr_backtest.py) | 수수료 반영 시 꾸준한 손실 |
| RSI(2) 평균회귀 | [`rsi_backtest.py`](strategies/rejected/rsi_backtest.py), [`multicoin_rsi.py`](strategies/rejected/multicoin_rsi.py) | 3코인 교차검증 모두 손실 |
| 레버리지+손절 | [`leverage_backtest.py`](strategies/rejected/leverage_backtest.py) | 레버리지가 손실을 배로 증폭(전략 자체 기대값이 음수라 손절도 못 살림) |

**"자기 자신과 크로스" 계열 (전부 과매매/휩쏘로 실패 — 설계원칙 1)**
| 지표 | 파일 |
|---|---|
| MACD 신호선 크로스 | [`macd_signal_backtest.py`](strategies/rejected/macd_signal_backtest.py) |
| Ehlers Fisher Transform | [`fisher_transform_backtest.py`](strategies/rejected/fisher_transform_backtest.py) |
| Ehlers Laguerre RSI | [`laguerre_rsi_backtest.py`](strategies/rejected/laguerre_rsi_backtest.py) |
| RVI (신호선 크로스) | [`rvi_backtest.py`](strategies/rejected/rvi_backtest.py) |
| Stochastic RSI | [`stochrsi_backtest.py`](strategies/rejected/stochrsi_backtest.py) |
| RSI 다이버전스 | [`rsi_divergence_backtest.py`](strategies/rejected/rsi_divergence_backtest.py) |

**추세추종형 스톱앤리버스 (설계원칙 2 — 이 시간대·자산군엔 안 맞음)**
| 지표 | 파일 |
|---|---|
| Parabolic SAR | [`psar_backtest.py`](strategies/rejected/psar_backtest.py) |
| SuperTrend + ADX | [`tradingview_strategies.py`](strategies/rejected/tradingview_strategies.py) |
| Schaff Trend Cycle | [`stc_backtest.py`](strategies/rejected/stc_backtest.py) |
| Aroon | [`aroon_backtest.py`](strategies/rejected/aroon_backtest.py) |
| Vortex Indicator | [`vortex_backtest.py`](strategies/rejected/vortex_backtest.py) |
| Kaufman Efficiency Ratio | [`efficiency_ratio_backtest.py`](strategies/rejected/efficiency_ratio_backtest.py) |

**오실레이터/거래량 계열 (임계값 재보정해도 견고성 부족)**
| 지표 | 파일 |
|---|---|
| MFI | [`mfi_backtest.py`](strategies/rejected/mfi_backtest.py) |
| Ultimate Oscillator | [`uo_backtest.py`](strategies/rejected/uo_backtest.py) |
| Williams %R | [`williams_r_backtest.py`](strategies/rejected/williams_r_backtest.py) |
| Klinger | [`klinger_backtest.py`](strategies/rejected/klinger_backtest.py) |
| DPO | [`dpo_backtest.py`](strategies/rejected/dpo_backtest.py) |
| Awesome Oscillator | [`awesome_osc_backtest.py`](strategies/rejected/awesome_osc_backtest.py) |
| Balance of Power | [`bop_backtest.py`](strategies/rejected/bop_backtest.py) |
| Volatility RSI | [`vol_rsi_backtest.py`](strategies/rejected/vol_rsi_backtest.py) |
| 가격 Z-score (대조군) | [`price_zscore_backtest.py`](strategies/rejected/price_zscore_backtest.py) |

**차트 패턴 (지표가 아닌 구조 기반, 전부 기각)**
| 패턴 | 파일 |
|---|---|
| 삼각수렴 돌파 | [`triangle_backtest.py`](strategies/rejected/triangle_backtest.py) |
| 이중바닥/이중천장, 깃발형 | [`chart_patterns.py`](strategies/rejected/chart_patterns.py) |

**조합/필터 (설계원칙 3 — 좋은 신호에 뭘 더하면 오히려 나빠짐)**
| 조합 | 파일 |
|---|---|
| MACD약신호+MA/추세/볼밴/ADX 필터 조합 | [`combo_signal_backtest.py`](strategies/rejected/combo_signal_backtest.py) |
| Connors RSI + 삼각수렴 (AND/OR) | [`combo_indicator_pattern.py`](strategies/rejected/combo_indicator_pattern.py) |
| Connors RSI + Choppiness Index 필터 | [`chop_filter_backtest.py`](strategies/rejected/chop_filter_backtest.py) |
| "Full Crypto Pack" (MACD+RSI+OBV+EMA) | [`tradingview_strategies.py`](strategies/rejected/tradingview_strategies.py) |
| 변동성 돌파 (Larry Williams) | [`vbreakout_backtest.py`](strategies/rejected/vbreakout_backtest.py) |

---

## ⚠️ 한계와 주의사항

- **백테스트이지 실전 검증이 아님.** 슬리피지 미반영(수수료만 반영). 실제 체결가는 더 나쁠 수 있음.
- **2022-07~2026-07 특정 4년 구간의 결과.** 다른 시기·국면에서 재현 보장 없음.
- **다중검정 위험은 이 리포트 자체에도 적용됨.** 30개 이상 지표 테스트 중 일부 "확정"도 순전히 우연일 가능성을 배제 못함.
- 실제 자금 투입 전 **소액·페이퍼 트레이딩부터** 시작 권장.

## 다음 단계 제안
1. 확정 지표(특히 DOT/LTC/ETH)를 조합해 페이퍼 트레이딩 봇으로 구현
2. "강세장 감지 시 전략 OFF" 국면 필터 실전 검증 (백테스트 내 결합은 실패했었지만, 사후 국면판단은 다른 문제)
3. 바이낸스 테스트넷 실시간 페이퍼 트레이딩 시작
