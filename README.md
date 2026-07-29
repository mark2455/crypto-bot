# crypto-bot — 바이낸스 선물 테스트넷 자동매매 봇 (학습용)

> ⚠️ **전부 가짜 돈(테스트넷)입니다.** 실제 돈은 한 푼도 걸려 있지 않습니다.
> 전략이 충분히 검증되기 전에는 절대 실계좌/실돈으로 옮기지 마세요.

## 지금까지 된 것 (1단계)
- Python 가상환경 + 라이브러리(ccxt, pandas, python-dotenv) 설치
- 바이낸스 **선물 테스트넷** 연결 확인
- BTC/USDT 현재가 조회 성공

## 폴더 구성
| 파일 | 역할 |
|---|---|
| `config.py` | 거래소 연결 설정 (테스트넷 고정, 키는 .env 에서 읽음) |
| `check.py` | 연결·현재가·잔고 점검 스크립트 |
| `.env.example` | API 키 템플릿 (복사해서 `.env` 로 채움) |
| `requirements.txt` | 라이브러리 목록 |
| `venv/` | 가상환경 (git 제외) |

## 실행 방법
```bash
cd ~/crypto-bot
venv/bin/python check.py
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
5. 다시 `venv/bin/python check.py` 실행하면 잔고가 표시됨

## 다음 단계 (예정)
- 2단계: 캔들(OHLCV) 데이터 받아서 pandas 로 다루기
- 3단계: 백테스팅 엔진 (과거 데이터로 규칙 검증, 수수료 포함)
- 4단계: 페이퍼 트레이딩 (실시간 + 가짜 주문)
- 5단계: 전략/리스크 관리 개선
