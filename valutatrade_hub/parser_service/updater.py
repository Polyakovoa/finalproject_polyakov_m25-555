"""Основной модуль обновления курсов валют."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from ..core.currencies import CurrencyNotFoundError, get_currency
from .api_clients import RateAPIClient
from .storage import RateStorage

logger = logging.getLogger("valutatrade.parser")


class RateUpdater:
    """Класс для обновления курсов валют."""

    def __init__(self):
        self.api_client = RateAPIClient()
        self.storage = RateStorage()
        self.updated_pairs: List[str] = []

    def update_rates(self) -> Dict[str, Any]:
        """
        Основной метод обновления всех курсов валют.

        Returns:
            Статистика обновления
        """
        logger.info("Starting currency rates update")

        stats = {
            "total_updated": 0,
            "fiat_rates": 0,
            "crypto_rates": 0,
            "errors": 0,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        try:
            # Получаем все курсы из API
            all_rates_data = self.api_client.get_all_rates()
            logger.info(f"Received data structure: {list(all_rates_data.keys())}")

            # Обрабатываем фиатные курсы
            if "fiat_data" in all_rates_data:
                fiat_data = all_rates_data["fiat_data"]
                logger.info(f"Fiat data source: {fiat_data.get('source')}, rates count: {len(fiat_data.get('rates', {}))}") # noqa: E501
                if "rates" in fiat_data and fiat_data.get("source") == "ExchangeRate-API": # noqa: E501
                    fiat_stats = self._process_fiat_rates(fiat_data)
                    stats["fiat_rates"] = fiat_stats["fiat_rates"]
                    stats["total_updated"] += fiat_stats["fiat_rates"]
                else:
                    logger.warning(f"Invalid fiat data: source={fiat_data.get('source')}, has_rates={'rates' in fiat_data}") # noqa: E501

            # Обрабатываем крипто курсы
            if "crypto_data" in all_rates_data:
                crypto_data = all_rates_data["crypto_data"]
                logger.info(f"Crypto data source: {crypto_data.get('source')}, rates count: {len(crypto_data.get('rates', {}))}") # noqa: E501
                if "rates" in crypto_data and crypto_data.get("source") == "CoinGecko":
                    crypto_stats = self._process_crypto_rates(crypto_data)
                    stats["crypto_rates"] = crypto_stats.get("crypto_rates", 0)
                    stats["total_updated"] += crypto_stats.get("crypto_rates", 0)
                else:
                    logger.warning(f"Invalid crypto data: source={crypto_data.get('source')}, has_rates={'rates' in crypto_data}") # noqa: E501

            logger.info(f"Rates update completed: {stats}")

        except Exception as e:
            logger.error(f"Failed to update rates: {e}")
            import traceback
            logger.error(traceback.format_exc())
            stats["errors"] += 1

        return stats

    def _process_fiat_rates(self, rates_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает фиатные курсы из ExchangeRate-API."""
        # Проверяем что это данные от ExchangeRate-API
        if rates_data.get("source") != "ExchangeRate-API":
            logger.warning(f"Not processing fiat rates from source: {rates_data.get('source')}") # noqa: E501
            return {"fiat_rates": 0}

        base_currency = rates_data["base_currency"]
        rates = rates_data["rates"]
        timestamp = rates_data["timestamp"]
        source = rates_data["source"]

        stats = {"fiat_rates": 0}

        logger.info(f"Processing fiat rates for {base_currency}, {len(rates)} currencies available") # noqa: E501

        # Обрабатываем все доступные фиатные валюты
        target_currencies = ["EUR", "GBP", "JPY", "RUB", "CHF", "CNY"]

        for currency_code in target_currencies:
            if currency_code not in rates:
                logger.debug(f"Currency {currency_code} not in API response")
                continue

            rate = rates[currency_code]

            # Валидируем код валюты
            try:
                get_currency(currency_code)
            except CurrencyNotFoundError:
                logger.warning(f"Skipping unknown currency: {currency_code}")
                continue

            # Сохраняем прямую котировку (base -> currency)
            rate_record = {
                "from_currency": base_currency,
                "to_currency": currency_code,
                "rate": float(rate),
                "timestamp": timestamp,
                "source": source,
                "meta": {
                    "request_ms": rates_data.get("meta", {}).get("request_ms", 0),
                    "status_code": 200
                }
            }

            try:
                # Сохраняем курс (не сохраняем возвращаемый ID)
                self.storage.save_rate(rate_record)
                stats["fiat_rates"] += 1
                self.updated_pairs.append(f"{base_currency}_{currency_code}")
                logger.info(f"Saved fiat rate: {base_currency} -> {currency_code} = {rate}")  # noqa: E501
            except Exception as e:
                logger.error(f"Failed to save rate for {currency_code}: {e}")

        logger.info(f"Processed {stats['fiat_rates']} fiat rates out of {len(target_currencies)} target currencies") # noqa: E501
        return stats

    def _process_crypto_rates(self, crypto_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает крипто курсы из CoinGecko."""
        # Проверяем, что это данные от CoinGecko и есть курсы
        if crypto_data.get("source") != "CoinGecko" or not crypto_data.get("rates"):
            logger.warning(f"Not processing crypto rates from source: {crypto_data.get('source')} or no rates available")  # noqa: E501
            return {"crypto_rates": 0}

        base_currency = crypto_data["base_currency"]
        rates = crypto_data["rates"]
        timestamp = crypto_data["timestamp"]
        source = crypto_data["source"]

        stats = {"crypto_rates": 0}

        logger.info(f"Processing crypto rates for {base_currency}, {len(rates)} currencies available") # noqa: E501

        for currency_code, rate in rates.items():
            # Валидируем код валюты
            try:
                get_currency(currency_code)
            except CurrencyNotFoundError:
                logger.warning(f"Skipping unknown crypto currency: {currency_code}")
                continue

            # Сохраняем прямую котировку (crypto -> base)
            rate_record = {
                "from_currency": currency_code,
                "to_currency": base_currency,
                "rate": float(rate),
                "timestamp": timestamp,
                "source": source,
                "meta": {
                    "request_ms": crypto_data.get("meta", {}).get("request_ms", 0),
                    "status_code": 200
                }
            }

            try:
                # Сохраняем курс
                self.storage.save_rate(rate_record)
                stats["crypto_rates"] += 1
                self.updated_pairs.append(f"{currency_code}_{base_currency}")
                logger.info(f"Saved crypto rate: {currency_code} -> {base_currency} = {rate}") # noqa: E501
            except Exception as e:
                logger.error(f"Failed to save crypto rate for {currency_code}: {e}")

        logger.info(f"Processed {stats['crypto_rates']} crypto rates")
        return stats

    def update_local_cache(self) -> bool:
        """
        Обновляет локальный кэш rates.json из исторических данных.

        Returns:
            True если обновление успешно
        """
        try:
            # Получаем последние курсы
            latest_rates = self.storage.get_latest_rates("USD")

            # Создаем структуру для rates.json
            cache_data = {
                "source": "ParserService",
                "last_refresh": datetime.utcnow().isoformat() + "Z",
                "rates": {}
            }

            # Добавляем все пары валют
            for currency, rate in latest_rates.items():
                pair_key = f"{currency}_USD"
                cache_data["rates"][pair_key] = {
                    "rate": rate,
                    "updated_at": datetime.utcnow().isoformat() + "Z"
                }

            # Сохраняем в rates.json через DatabaseManager
            from ..infra.database import db
            db.save("rates", cache_data)

            logger.info(f"Local cache updated with {len(latest_rates)} rates")
            return True

        except Exception as e:
            logger.error(f"Failed to update local cache: {e}")
            return False

    def get_update_status(self) -> Dict[str, Any]:
        """Возвращает статус последнего обновления."""
        return {
            "last_updated_pairs": self.updated_pairs,
            "total_pairs": len(self.updated_pairs),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
