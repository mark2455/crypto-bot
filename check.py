"""
1단계 점검 스크립트.
- 거래소 연결 확인
- BTC/USDT 현재가 조회 (API 키 없어도 됨)
- 잔고 조회 (.env 에 테스트넷 키를 넣으면 동작)

실행:  ~/crypto-bot/venv/bin/python check.py
"""
from config import make_exchange, has_keys, SYMBOL


def main():
    ex = make_exchange()

    # 1) 현재가 (공개 데이터 — 키 불필요)
    ticker = ex.fetch_ticker(SYMBOL)
    print(f"[연결 OK] 바이낸스 선물 테스트넷")
    print(f"  {SYMBOL} 현재가: {ticker['last']} USDT")

    # 2) 잔고 (키 필요)
    if not has_keys():
        print("\n[안내] .env 에 테스트넷 API 키가 아직 없습니다.")
        print("  README 의 '테스트넷 키 발급'을 따라 키를 넣으면 잔고가 표시됩니다.")
        return

    balance = ex.fetch_balance()
    usdt = balance["total"].get("USDT", 0)
    print(f"\n[잔고 OK] 테스트넷 USDT 잔고: {usdt}")


if __name__ == "__main__":
    main()
