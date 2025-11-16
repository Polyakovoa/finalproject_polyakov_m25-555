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

            # Обрабатываем фиатные курсы
            if "rates" in all_rates_data and "base_currency" in all_rates_data:
                fiat_stats = self._process_fiat_rates(all_rates_data)
                stats.update(fiat_stats)

            # Обрабатываем крипто курсы (могут быть в отдельном ключе или том же)
            if "rates" in all_rates_data:  # CoinGecko тоже использует ключ "rates"
                crypto_stats = self._process_crypto_rates(all_rates_data)
                stats["crypto_rates"] = crypto_stats.get("crypto_rates", 0)
                stats["total_updated"] += crypto_stats.get("crypto_rates", 0)

            logger.info(f"Rates update completed: {stats['total_updated']} rates updated")  # noqa: E501

        except Exception as e:
            logger.error(f"Failed to update rates: {e}")
            stats["errors"] += 1

        return stats

    def _process_fiat_rates(self, rates_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает фиатные курсы из ExchangeRate-API."""
        base_currency = rates_data["base_currency"]
        rates = rates_data["rates"]
        timestamp = rates_data["timestamp"]
        source = rates_data["source"]

        stats = {"fiat_rates": 0}

        for currency_code, rate in rates.items():
            # Пропускаем базовую валюту
            if currency_code == base_currency:
                continue

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
                self.storage.save_rate(rate_record)
                stats["fiat_rates"] += 1
                self.updated_pairs.append(f"{base_currency}_{currency_code}")
                logger.debug(f"Saved rate: {base_currency} -> {currency_code} = {rate}")
            except Exception as e:
                logger.error(f"Failed to save rate for {currency_code}: {e}")

        return stats

    def _process_crypto_rates(self, rates_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает крипто курсы из CoinGecko."""
        # Проверяем, что это данные от CoinGecko
        if rates_data.get("source") != "CoinGecko":
            return {"crypto_rates": 0}

        base_currency = rates_data["base_currency"]
        rates = rates_data["rates"]
        timestamp = rates_data["timestamp"]
        source = rates_data["source"]

        stats = {"crypto_rates": 0}

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
                    "request_ms": rates_data.get("meta", {}).get("request_ms", 0),
                    "status_code": 200
                }
            }

            try:
                self.storage.save_rate(rate_record)
                stats["crypto_rates"] += 1
                self.updated_pairs.append(f"{currency_code}_{base_currency}")
                logger.debug(f"Saved crypto rate: {currency_code} -> {base_currency} = {rate}")  # noqa: E501
            except Exception as e:
                logger.error(f"Failed to save crypto rate for {currency_code}: {e}")

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
