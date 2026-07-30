# crypto-bot — 바이낸스 선물 테스트넷 자동매매 전략 연구 (학습용)

> ⚠️ **전부 가짜 돈(테스트넷)입니다.** 실제 돈은 한 푼도 걸려 있지 않습니다.
> 전략이 충분히 검증되기 전에는 절대 실계좌/실돈으로 옮기지 마세요.

## 지금까지 된 것
1시간봉·4년치(2022-07~2026-07) 데이터로 30개 이상의 기술적 지표를 검증해서, 9개 코인
(DOT/LINK/ETC/LTC/SOL/BNB/BTC/ETH/XRP) 각각에 **4개 연도 구간 전부 플러스(4/4)** 인
전략을 최소 1개 이상 확정했다. 전체 방법론·결과·진입·청산 규칙은 **[`RESULTS.md`](RESULTS.md)** 참고.

## 폴더 구성
검증 결과에 따라 코드를 분리해뒀다 — **확정된 것과 폐기된 것이 섞이지 않도록**.

| 위치 | 내용 |
|---|---|
| `candles.py`, `config.py`, `check.py`, `fetch_history.py`, `indicator_analysis.py` | 공통 인프라 — 데이터 로딩, 거래소 연결, 공용 지표 함수 |
| `connors_rsi_backtest.py` | 최초 확정 전략(Connors RSI, 기준선) — 다른 여러 파일이 공유 참조하므로 루트에 위치 |
| `strategies/confirmed/` | ✅ **4/4년 검증 통과** — 실전 적용 가능한 17개 전략 파일 |
| `strategies/rejected/` | ❌ **기각/탈락** — 검증에서 떨어진 33개 지표·패턴·조합 (실패 이유도 기록해둠) |
| `strategies/loop_log.md` | 지표 하나씩 검증한 상세 원본 로그 (30개 이상) |
| `experiments/other_markets/` | 크립토 4/4 검증 틀 밖의 별도 실험 (한국/미국 주식 페어트레이딩, 계절성 등) — 이 결과들과 무관, 참고용 |
| `.env.example` | API 키 템플릿 (복사해서 `.env` 로 채움) |
| `requirements.txt` | 라이브러리 목록 |
| `venv/` | 가상환경 (git 제외) |

## 실행 방법
스크립트가 하위 폴더로 옮겨지면서, 루트의 공통 모듈(`candles.py` 등)을 찾도록
`PYTHONPATH=.` 를 붙여서 실행한다 (**항상 `~/crypto-bot` 에서** 실행):

```bash
cd ~/crypto-bot
venv/bin/python check.py                                        # 연결 점검 (루트 파일은 그대로)
PYTHONPATH=. venv/bin/python strategies/confirmed/keltner_backtest.py   # 확정 전략 재실행
PYTHONPATH=. venv/bin/python strategies/rejected/rvi_backtest.py        # 기각 전략도 그대로 재현 가능
```

## 테스트넷 키 발급 (선택 — 잔고/주문 기능 쓰려면)
1. https://testnet.binancefuture.com 접속 → GitHub 계정으로 로그인
2. 로그인하면 자동으로 가짜 USDT가 지급됨
3. 하단 **API Key** 탭에서 키 생성 → API Key / Secret 복사
4. 키를 파일에 저장:
   ```bash
   cd ~/crypto-bot
   cp .env.example .env
   # .env 파일을 열어 두 줄에 복사한 값 붙여넣기
   ```
5. `venv/bin/python check.py` 실행하면 잔고가 표시됨

## 다음 단계
`RESULTS.md` 맨 아래 "다음 단계 제안" 참고 — 확정 전략 페이퍼 트레이딩 봇 구현이 다음 순서.
