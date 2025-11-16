"""Основной модуль обновления курсов валют."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .storage import RateStorage

logger = logging.getLogger("valutatrade.parser")


class RatesUpdater:
    """Координирует процесс обновления курсов валют."""

    def __init__(self, storage: RateStorage = None):
        self.storage = storage or RateStorage()
        self.api_clients = {
            "fiat": ExchangeRateApiClient(),
            "crypto": CoinGeckoClient()
        }
        self.updated_pairs: List[str] = []

    def run_update(self) -> Dict[str, Any]:
        """
        Основной метод обновления всех курсов валют.

        Returns:
            Статистика обновления в формате для CLI
        """
        logger.info("🚀 Starting currency rates update process")

        stats = {
            "total_pairs": 0,
            "successful_sources": 0,
            "failed_sources": 0,
            "sources": {},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        # Собираем все курсы от всех источников
        all_rates = {}

        # Опрашиваем каждый API клиент
        for source_type, client in self.api_clients.items():
            try:
                logger.info(f"📡 Fetching rates from {source_type} source")
                rates = client.fetch_rates()

                all_rates.update(rates)
                stats["sources"][source_type] = {
                    "status": "success",
                    "pairs_count": len(rates),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                stats["successful_sources"] += 1
                stats["total_pairs"] += len(rates)

                logger.info(f"✅ {source_type}: fetched {len(rates)} rate pairs")

            except Exception as e:
                logger.error(f"❌ {source_type}: failed to fetch rates - {e}")
                stats["sources"][source_type] = {
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                stats["failed_sources"] += 1

        # Сохраняем исторические данные
        historical_stats = self._save_historical_data(all_rates)
        stats.update(historical_stats)

        # Обновляем локальный кэш
        cache_success = self._update_local_cache(all_rates)
        stats["cache_updated"] = cache_success

        logger.info(f"✅ Update completed: {stats['total_pairs']} pairs, "
                   f"{stats['successful_sources']} successful sources")

        return self._format_cli_stats(stats)

    def _save_historical_data(self, rates: Dict[str, float]) -> Dict[str, Any]:
        """Сохраняет курсы в историческое хранилище."""
        saved_records = 0
        current_time = datetime.utcnow().isoformat() + "Z"

        for pair_key, rate in rates.items():
            try:
                # Парсим пару валют (формат: "FROM_TO")
                from_currency, to_currency = pair_key.split("_")

                # Определяем источник по типу валюты
                source = "CoinGecko" if self._is_crypto(from_currency) else "ExchangeRate-API" # noqa: E501

                rate_record = {
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "rate": float(rate),
                    "timestamp": current_time,
                    "source": source,
                    "meta": {
                        "request_ms": 0,
                        "status_code": 200
                    }
                }

                # Сохраняем в историческое хранилище
                self.storage.save_rate(rate_record)
                saved_records += 1
                self.updated_pairs.append(pair_key)

                logger.debug(f"💾 Saved historical rate: {pair_key} = {rate}")

            except Exception as e:
                logger.error(f"Failed to save historical rate for {pair_key}: {e}")

        return {
            "historical_records_saved": saved_records,
            "historical_pairs": self.updated_pairs
        }

    def _update_local_cache(self, rates: Dict[str, float]) -> bool:
        """Обновляет локальный кэш rates.json."""
        try:
            current_time = datetime.utcnow().isoformat() + "Z"

            cache_data = {
                "pairs": {},
                "last_refresh": current_time,
                "source": "ParserService"
            }

            # Преобразуем курсы в формат для rates.json
            for pair_key, rate in rates.items():
                from_currency, to_currency = pair_key.split("_")

                # Определяем источник для отображения
                source = "CoinGecko" if self._is_crypto(from_currency) else "ExchangeRate-API" # noqa: E501

                cache_data["pairs"][pair_key] = {
                    "rate": float(rate),
                    "updated_at": current_time,
                    "source": source
                }

            # Сохраняем через DatabaseManager
            from ..infra.database import db
            db.save("rates", cache_data)

            logger.info(f"💾 Local cache updated with {len(cache_data['pairs'])} rate pairs") # noqa: E501
            return True

        except Exception as e:
            logger.error(f"❌ Failed to update local cache: {e}")
            return False

    def _is_crypto(self, currency_code: str) -> bool:
        """Проверяет, является ли валюта криптовалютой."""
        crypto_currencies = {"BTC", "ETH", "LTC", "XRP", "ADA", "SOL", "DOT"}
        return currency_code in crypto_currencies

    def _format_cli_stats(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Форматирует статистику для вывода в CLI."""
        fiat_count = stats["sources"].get("fiat", {}).get("pairs_count", 0)
        crypto_count = stats["sources"].get("crypto", {}).get("pairs_count", 0)

        return {
            "total_updated": stats["total_pairs"],
            "fiat_rates": fiat_count,
            "crypto_rates": crypto_count,
            "errors": stats["failed_sources"],
            "timestamp": stats["timestamp"],
            "details": stats
        }

    def get_update_status(self) -> Dict[str, Any]:
        """Возвращает статус последнего обновления."""
        return {
            "last_updated_pairs": self.updated_pairs,
            "total_pairs": len(self.updated_pairs),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
