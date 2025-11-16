"""Клиенты для работы с внешними API курсов валют."""

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from ..core.exceptions import ApiRequestError
from .config import ParserConfig

logger = logging.getLogger("valutatrade.parser")


class BaseAPIClient:
    """Базовый клиент для работы с API."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ValutaTrade-Hub/1.0",
            "Accept": "application/json"
        })

    def _make_request(self, url: str, params: Optional[Dict] = None, method: str = "GET") -> Dict[str, Any]:  # noqa: E501
        """Выполняет HTTP запрос с повторными попытками."""
        for attempt in range(ParserConfig.MAX_RETRIES):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=ParserConfig.REQUEST_TIMEOUT
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Too Many Requests
                    logger.warning(f"Rate limit exceeded, attempt {attempt + 1}")
                    if attempt < ParserConfig.MAX_RETRIES - 1:
                        time.sleep(ParserConfig.RETRY_DELAY * (attempt + 1))
                        continue
                else:
                    logger.error(f"API error: {response.status_code} - {response.text}")

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout, attempt {attempt + 1}")
                if attempt < ParserConfig.MAX_RETRIES - 1:
                    time.sleep(ParserConfig.RETRY_DELAY * (attempt + 1))
                    continue
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error, attempt {attempt + 1}")
                if attempt < ParserConfig.MAX_RETRIES - 1:
                    time.sleep(ParserConfig.RETRY_DELAY * (attempt + 1))
                    continue
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                if attempt < ParserConfig.MAX_RETRIES - 1:
                    time.sleep(ParserConfig.RETRY_DELAY * (attempt + 1))
                    continue

        raise ApiRequestError(f"Failed to fetch data after {ParserConfig.MAX_RETRIES} attempts") # noqa: E501


class ExchangeRateAPIClient(BaseAPIClient):
    """Клиент для работы с ExchangeRate-API (фиатные валюты)."""

    def get_exchange_rates(self, base_currency: str = "USD") -> Dict[str, Any]:
        """Получает курсы фиатных валют относительно базовой валюты."""
        url = ParserConfig.get_exchangerate_url(base_currency)

        try:
            data = self._make_request(url)

            if data.get("result") != "success":
                raise ApiRequestError(f"ExchangeRate-API error: {data.get('error-type', 'Unknown error')}") # noqa: E501

            # Проверяем наличие ключа rates
            if "conversion_rates" in data:
                rates_key = "conversion_rates"
            elif "rates" in data:
                rates_key = "rates"
            else:
                raise ApiRequestError("ExchangeRate-API response missing rates data")

            return {
                "base_currency": base_currency,
                "rates": data[rates_key],
                "timestamp": data.get("time_last_update_utc", datetime.utcnow().isoformat() + "Z"),  # noqa: E501
                "source": "ExchangeRate-API"
            }

        except ApiRequestError:
            raise
        except Exception as e:
            raise ApiRequestError(f"Failed to parse ExchangeRate-API response: {e}")

class CoinGeckoAPIClient(BaseAPIClient):
    """Клиент для работы с CoinGecko API (криптовалюты)."""

    def get_crypto_rates(self, vs_currency: str = "usd") -> Dict[str, Any]:
        """Получает курсы криптовалют относительно указанной валюты."""
        params = ParserConfig.get_coingecko_params(vs_currency)

        try:
            data = self._make_request(ParserConfig.COINGECKO_API_URL, params)

            # Преобразуем данные в единый формат
            rates = {}
            for crypto_code, gecko_id in ParserConfig.CRYPTO_ID_MAP.items():
                if gecko_id in data and vs_currency in data[gecko_id]:
                    rates[crypto_code] = data[gecko_id][vs_currency]

            return {
                "base_currency": vs_currency.upper(),
                "rates": rates,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "CoinGecko"
            }

        except ApiRequestError:
            raise
        except Exception as e:
            raise ApiRequestError(f"Failed to parse CoinGecko response: {e}")


class RateAPIClient:
    """Общий клиент для работы со всеми API курсов."""

    def __init__(self):
        self.exchangerate_client = ExchangeRateAPIClient()
        self.coingecko_client = CoinGeckoAPIClient()

    def get_all_rates(self) -> Dict[str, Any]:
        """Получает все курсы валют из всех источников."""
        all_rates = {}

        try:
            # Получаем фиатные курсы
            fiat_rates = self.exchangerate_client.get_exchange_rates("USD")
            # Используем фиатные данные как основу
            all_rates.update(fiat_rates)
            logger.info(f"Fiat rates: {len(fiat_rates.get('rates', {}))} currencies")
        except ApiRequestError as e:
            logger.error(f"Failed to fetch fiat rates: {e}")
            # Создаем базовую структуру
            all_rates.update({
                "base_currency": "USD",
                "rates": {},
                "source": "ExchangeRate-API-failed",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })

        try:
            # Получаем крипто курсы
            crypto_rates = self.coingecko_client.get_crypto_rates("usd")
            logger.info(f"Crypto rates raw: {crypto_rates}")

            # Возвращаем отдельно крипто данные для обработки
            return {
                "fiat_data": all_rates,
                "crypto_data": crypto_rates
            }

        except ApiRequestError as e:
            logger.error(f"Failed to fetch crypto rates: {e}")
            # Если крипто не сработало, возвращаем только фиатные
            return {
                "fiat_data": all_rates,
                "crypto_data": {
                    "base_currency": "USD",
                    "rates": {},
                    "source": "CoinGecko-failed",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            }
