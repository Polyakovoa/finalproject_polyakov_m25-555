"""Конфигурация для Parser Service."""

from typing import Dict, List

from ..infra.settings import settings


class ParserConfig:
    """Конфигурация парсера курсов валют."""

    # API ключи (добавьте свои реальные ключи)
    EXCHANGERATE_API_KEY = settings.get("exchangerate_api_key", "4b468e05030488a5d11e381c")  # noqa: E501
    COINGECKO_API_KEY = settings.get("coingecko_api_key", "")

    # URL API endpoints
    EXCHANGERATE_API_URL = "https://v6.exchangerate-api.com/v6/{key}/latest/{base_currency}"  # noqa: E501
    COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

    # Таймауты и повторные попытки
    REQUEST_TIMEOUT = settings.get("api_timeout_seconds", 30)
    MAX_RETRIES = settings.get("api_max_retries", 3)
    RETRY_DELAY = settings.get("api_retry_delay", 1.0)

    # Интервал обновления (в секундах)
    UPDATE_INTERVAL = settings.get("rates_update_interval", 300)  # 5 минут

    # Поддерживаемые валюты
    SUPPORTED_FIAT_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "RUB", "CHF", "CNY"]
    SUPPORTED_CRYPTO_CURRENCIES = ["BTC", "ETH", "LTC", "XRP", "ADA", "SOL", "DOT"]

    # Соответствие ID криптовалют в CoinGecko
    CRYPTO_ID_MAP: Dict[str, str] = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "LTC": "litecoin",
        "XRP": "ripple",
        "ADA": "cardano",
        "SOL": "solana",
        "DOT": "polkadot"
    }

    # Базовые валюты для конвертации
    BASE_CURRENCIES = ["USD"]

    @classmethod
    def get_exchangerate_url(cls, base_currency: str = "USD") -> str:
        """Возвращает URL для ExchangeRate-API."""
        return cls.EXCHANGERATE_API_URL.format(
            key=cls.EXCHANGERATE_API_KEY,
            base_currency=base_currency
        )

    @classmethod
    def get_coingecko_params(cls, vs_currency: str = "usd") -> Dict[str, str]:
        """Возвращает параметры для CoinGecko API."""
        crypto_ids = ",".join(cls.CRYPTO_ID_MAP.values())
        return {
            "ids": crypto_ids,
            "vs_currencies": vs_currency
        }

    @classmethod
    def get_supported_currencies(cls) -> List[str]:
        """Возвращает список всех поддерживаемых валют."""
        return cls.SUPPORTED_FIAT_CURRENCIES + cls.SUPPORTED_CRYPTO_CURRENCIES
