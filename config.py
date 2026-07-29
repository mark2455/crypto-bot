"""
거래소 연결 설정 (한 곳에서 관리).
- 바이낸스 선물 '테스트넷'(가짜 돈)에 연결합니다.
- API 키는 .env 파일에서 읽습니다. 코드에 절대 직접 쓰지 마세요.
"""
import os
import ccxt
from dotenv import load_dotenv

load_dotenv()  # 같은 폴더의 .env 를 읽어옴

SYMBOL = "BTC/USDT"   # 다룰 종목 (선물)


# 바이낸스 선물 테스트넷 도메인 (가짜 돈)
# ※ ccxt 최신 버전은 선물용 set_sandbox_mode 를 막아서, URL 을 직접 테스트넷으로 지정한다.
_TESTNET = "https://testnet.binancefuture.com"


def make_exchange():
    """바이낸스 선물 테스트넷 거래소 객체를 만든다."""
    api_key = os.getenv("BINANCE_TESTNET_API_KEY")
    api_secret = os.getenv("BINANCE_TESTNET_API_SECRET")

    exchange = ccxt.binance({
        "apiKey": api_key,
        "secret": api_secret,
        "enableRateLimit": True,          # 호출 속도 자동 조절(밴 방지)
        "options": {
            "defaultType": "future",   # 선물 시장
            # 초기화 때 USDT 선물(linear)만 불러옴 (현물/마진 호출 차단)
            "fetchMarkets": {"types": ["linear"], "loadAllOptions": False},
        },
    })

    # 선물 관련 엔드포인트(공개/인증)를 모두 테스트넷 도메인으로 교체
    for key, url in exchange.urls["api"].items():
        if key.startswith("fapi"):
            exchange.urls["api"][key] = url.replace(
                "https://fapi.binance.com", _TESTNET
            )

    # 초기화 때 현물(spot) 인증 엔드포인트를 호출하지 않게 함
    # (테스트넷 키는 현물에서 무효 → "Invalid Api-Key ID" 방지)
    exchange.has["fetchCurrencies"] = False
    return exchange


def has_keys():
    """API 키가 .env 에 채워졌는지 확인."""
    key = os.getenv("BINANCE_TESTNET_API_KEY")
    return bool(key) and "여기에" not in key
