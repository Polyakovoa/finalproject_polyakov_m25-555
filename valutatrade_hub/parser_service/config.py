"""Конфигурация для Parser Service с использованием dataclasses."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from ..infra.settings import settings


@dataclass
class ParserConfig:
    """Конфигурация парсера курсов валют с использованием dataclasses."""

    # API ключи (загружаются из переменных окружения)
    EXCHANGERATE_API_KEY: str = field(
        default_factory=lambda: os.getenv(
            "EXCHANGERATE_API_KEY",
            "4b468e05030488a5d11e381c",  # Fallback для разработки
        )
    )
    COINGECKO_API_KEY: str = field(
        default_factory=lambda: os.getenv("COINGECKO_API_KEY", "")
    )  # noqa: E501

    # Эндпоинты API
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Базовая валюта
    BASE_CURRENCY: str = "USD"

    # Списки отслеживаемых валют
    FIAT_CURRENCIES: Tuple[str, ...] = ("USD", "EUR", "GBP", "JPY", "RUB", "CHF", "CNY")  # noqa: E501
    CRYPTO_CURRENCIES: Tuple[str, ...] = (
        "BTC",
        "ETH",
        "LTC",
        "XRP",
        "ADA",
        "SOL",
        "DOT",
    )  # noqa: E501

    # Соответствие ID криптовалют в CoinGecko
    CRYPTO_ID_MAP: Dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "LTC": "litecoin",
            "XRP": "ripple",
            "ADA": "cardano",
            "SOL": "solana",
            "DOT": "polkadot",
        }
    )

    # Параметры запросов
    REQUEST_TIMEOUT: int = field(
        default_factory=lambda: settings.get("api_timeout_seconds", 30)
    )  # noqa: E501
    MAX_RETRIES: int = field(default_factory=lambda: settings.get("api_max_retries", 3))  # noqa: E501
    RETRY_DELAY: float = field(
        default_factory=lambda: settings.get("api_retry_delay", 1.0)
    )  # noqa: E501

    # Интервал обновления (в секундах)
    UPDATE_INTERVAL: int = field(
        default_factory=lambda: settings.get("rates_update_interval", 300)
    )  # noqa: E501

    # Пути к файлам
    RATES_FILE_PATH: str = field(
        default_factory=lambda: str(
            Path(settings.get("data_dir", "data")) / "rates.json"
        )
    )  # noqa: E501
    HISTORY_FILE_PATH: str = field(
        default_factory=lambda: str(
            Path(settings.get("data_dir", "data")) / "exchange_rates.json"
        )
    )  # noqa: E501
    DATA_DIR: str = field(default_factory=lambda: str(settings.get("data_dir", "data")))  # noqa: E501

    # Методы для формирования URL
    def get_exchangerate_url(self, base_currency: str = None) -> str:
        """Возвращает URL для ExchangeRate-API."""
        base = base_currency or self.BASE_CURRENCY
        return f"{self.EXCHANGERATE_API_URL}/{self.EXCHANGERATE_API_KEY}/latest/{base}"

    def get_coingecko_params(self, vs_currency: str = None) -> Dict[str, str]:
        """Возвращает параметры для CoinGecko API."""
        vs_currency = vs_currency or self.BASE_CURRENCY.lower()
        crypto_ids = ",".join(self.CRYPTO_ID_MAP.values())
        return {"ids": crypto_ids, "vs_currencies": vs_currency}

    def get_supported_currencies(self) -> List[str]:
        """Возвращает список всех поддерживаемых валют."""
        return list(self.FIAT_CURRENCIES) + list(self.CRYPTO_CURRENCIES)

    def validate_config(self) -> bool:
        """Проверяет валидность конфигурации."""
        if (
            not self.EXCHANGERATE_API_KEY
            or self.EXCHANGERATE_API_KEY == "your_api_key_here"
        ):  # noqa: E501
            raise ValueError(
                "EXCHANGERATE_API_KEY не настроен. Установите переменную окружения EXCHANGERATE_API_KEY"  # noqa: E501
            )  # noqa: E501

        if not all(
            currency in self.CRYPTO_ID_MAP for currency in self.CRYPTO_CURRENCIES
        ):  # noqa: E501
            missing = set(self.CRYPTO_CURRENCIES) - set(self.CRYPTO_ID_MAP.keys())
            raise ValueError(f"Отсутствуют mapping для криптовалют: {missing}")

        return True


# Глобальный экземпляр конфигурации
config = ParserConfig()
