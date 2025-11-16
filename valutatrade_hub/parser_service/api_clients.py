"""Клиенты для работы с внешними API курсов валют."""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict

import requests
from requests.exceptions import RequestException

from ..core.exceptions import ApiRequestError
from .config import config

logger = logging.getLogger("valutatrade.parser")


class BaseApiClient(ABC):
    """Абстрактный базовый класс для API клиентов."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "ValutaTrade-Hub/1.0", "Accept": "application/json"}
        )

    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы валют и возвращает их в стандартизированном формате.

        Returns:
            Dict[str, float]: Словарь с курсами в формате { "BTC_USD": 59337.21, ... }

        Raises:
            ApiRequestError: При ошибках сети или API
        """
        pass

    def _make_request(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Выполняет HTTP запрос с повторными попытками и обработкой ошибок.

        Args:
            url: URL для запроса
            params: Параметры запроса

        Returns:
            Dict[str, Any]: Ответ API в формате JSON

        Raises:
            ApiRequestError: При неудачных попытках запроса
        """
        for attempt in range(config.MAX_RETRIES):
            try:
                logger.debug(f"API request attempt {attempt + 1}: {url}")
                response = self.session.get(
                    url=url, params=params, timeout=config.REQUEST_TIMEOUT
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Too Many Requests
                    logger.warning(f"Rate limit exceeded, attempt {attempt + 1}")
                    if attempt < config.MAX_RETRIES - 1:
                        time.sleep(config.RETRY_DELAY * (attempt + 1))
                        continue
                    else:
                        raise ApiRequestError("Rate limit exceeded")
                else:
                    logger.error(f"API error {response.status_code}: {response.text}")
                    raise ApiRequestError(
                        f"HTTP {response.status_code}: {response.text}"
                    )

            except RequestException as e:
                logger.warning(f"Request exception on attempt {attempt + 1}: {e}")
                if attempt < config.MAX_RETRIES - 1:
                    time.sleep(config.RETRY_DELAY * (attempt + 1))
                    continue
                else:
                    raise ApiRequestError(f"Network error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < config.MAX_RETRIES - 1:
                    time.sleep(config.RETRY_DELAY * (attempt + 1))
                    continue
                else:
                    raise ApiRequestError(f"Unexpected error: {e}")

        raise ApiRequestError(
            f"Failed to fetch data after {config.MAX_RETRIES} attempts"
        )


class CoinGeckoClient(BaseApiClient):
    """Клиент для работы с CoinGecko API (криптовалюты)."""

    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы криптовалют относительно USD.

        Returns:
            Dict[str, float]: Курсы в формате { "BTC_USD": 59337.21, ... }
        """
        try:
            params = config.get_coingecko_params("usd")
            data = self._make_request(config.COINGECKO_URL, params)

            # Преобразуем данные в стандартизированный формат
            rates = {}
            for crypto_code, gecko_id in config.CRYPTO_ID_MAP.items():
                if gecko_id in data and "usd" in data[gecko_id]:
                    rate_key = f"{crypto_code}_{config.BASE_CURRENCY}"
                    rates[rate_key] = data[gecko_id]["usd"]

            logger.info(f"Fetched {len(rates)} crypto rates from CoinGecko")
            return rates

        except ApiRequestError:
            raise
        except Exception as e:
            raise ApiRequestError(f"Failed to parse CoinGecko response: {e}")


class ExchangeRateApiClient(BaseApiClient):
    """Клиент для работы с ExchangeRate-API (фиатные валюты)."""

    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы фиатных валют относительно USD."""
        try:
            url = config.get_exchangerate_url("USD")
            data = self._make_request(url)

            # Проверяем успешность ответа API
            if data.get("result") != "success":
                error_type = data.get("error-type", "Unknown error")
                raise ApiRequestError(f"ExchangeRate-API error: {error_type}")

            # Извлекаем курсы из ответа
            rates_data = data.get("conversion_rates") or data.get("rates") or {}
            if not rates_data:
                raise ApiRequestError("ExchangeRate-API response missing rates data")

            # ФИКС: ИНВЕРТИРУЕМ КУРСЫ ДЛЯ ФИАТНЫХ ВАЛЮТ
            rates = {}
            base_currency = data.get("base_code", "USD")

            for currency in config.FIAT_CURRENCIES:
                if currency in rates_data and currency != base_currency:
                    rate_key = f"{currency}_{base_currency}"
                    # ИНВЕРСИЯ: 1 / курс, чтобы получить "количество USD за 1 валюту"
                    original_rate = float(rates_data[currency])
                    inverted_rate = 1.0 / original_rate
                    rates[rate_key] = inverted_rate

            logger.info(
                f"Fetched {len(rates)} fiat rates from ExchangeRate-API (inverted from {len(rates_data)} available)"  # noqa: E501
            )
            return rates

        except ApiRequestError:
            raise
        except Exception as e:
            raise ApiRequestError(f"Failed to parse ExchangeRate-API response: {e}")


class RateAPIClient:
    """Общий клиент для работы со всеми API курсов."""

    def __init__(self):
        self.exchangerate_client = ExchangeRateApiClient()
        self.coingecko_client = CoinGeckoClient()

    def get_all_rates(self) -> Dict[str, Any]:
        """Получает все курсы валют из всех источников.

        Returns:
            Dict[str, Any]: Объединенные данные курсов с метаданными
        """
        all_rates = {}
        metadata = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "base_currency": config.BASE_CURRENCY,
            "sources": {},
        }

        # Получаем фиатные курсы
        try:
            fiat_rates = self.exchangerate_client.fetch_rates()
            all_rates.update(fiat_rates)
            metadata["sources"]["fiat"] = {
                "source": "ExchangeRate-API",
                "currencies_count": len(fiat_rates),
            }
            logger.info(f"Successfully fetched {len(fiat_rates)} fiat rates")
        except ApiRequestError as e:
            logger.error(f"Failed to fetch fiat rates: {e}")
            metadata["sources"]["fiat"] = {
                "source": "ExchangeRate-API-failed",
                "error": str(e),
            }

        # Получаем крипто курсы
        try:
            crypto_rates = self.coingecko_client.fetch_rates()
            all_rates.update(crypto_rates)
            metadata["sources"]["crypto"] = {
                "source": "CoinGecko",
                "currencies_count": len(crypto_rates),
            }
            logger.info(f"Successfully fetched {len(crypto_rates)} crypto rates")
        except ApiRequestError as e:
            logger.error(f"Failed to fetch crypto rates: {e}")
            metadata["sources"]["crypto"] = {
                "source": "CoinGecko-failed",
                "error": str(e),
            }

        return {"rates": all_rates, "metadata": metadata}
