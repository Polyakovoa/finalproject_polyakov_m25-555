"""Модуль для работы с хранилищем исторических данных курсов."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..infra.settings import settings

logger = logging.getLogger("valutatrade.parser")


class RateStorage:
    """Класс для работы с хранилищем исторических данных курсов."""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or settings.get("data_dir", "data"))
        self.history_file = self.data_dir / "exchange_rates.json"
        self._ensure_storage_file()

    def _ensure_storage_file(self) -> None:
        """Создает файл хранилища, если он не существует."""
        self.data_dir.mkdir(exist_ok=True)
        if not self.history_file.exists():
            self.history_file.write_text("[]", encoding="utf-8")

    def _generate_rate_id(
        self, from_currency: str, to_currency: str, timestamp: str
    ) -> str:  # noqa: E501
        """Генерирует уникальный ID для записи курса."""
        # Нормализуем timestamp для использования в ID
        normalized_ts = (
            timestamp.replace(":", "").replace("-", "").replace(" ", "").split("+")[0]
        )  # noqa: E501
        return f"{from_currency}_{to_currency}_{normalized_ts}"

    def _load_history(self) -> List[Dict[str, Any]]:
        """Загружает исторические данные из файла."""
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_history(self, data: List[Dict[str, Any]]) -> None:
        """Сохраняет исторические данные в файл."""
        try:
            # Простая запись в файл вместо атомарной замены
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
            raise

    def save_rate(self, rate_data: Dict[str, Any]) -> str:
        """
        Сохраняет запись курса валюты в историю.

        Args:
            rate_data: Данные курса

        Returns:
            ID сохраненной записи
        """
        from_currency = rate_data["from_currency"]
        to_currency = rate_data["to_currency"]
        timestamp = rate_data["timestamp"]

        # Генерируем уникальный ID
        rate_id = self._generate_rate_id(from_currency, to_currency, timestamp)

        record = {
            "id": rate_id,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": float(rate_data["rate"]),
            "timestamp": timestamp,
            "source": rate_data["source"],
            "meta": rate_data.get("meta", {}),
        }

        # Загружаем текущую историю
        history = self._load_history()

        # Проверяем, нет ли уже такой записи
        existing_ids = {item["id"] for item in history}
        if rate_id not in existing_ids:
            history.append(record)
            self._save_history(history)

        return rate_id

    def get_latest_rates(self, base_currency: str = "USD") -> Dict[str, float]:
        """
        Возвращает последние курсы для всех валют относительно базовой.

        Args:
            base_currency: Базовая валюта

        Returns:
            Словарь с курсами {валюта: курс}
        """
        history = self._load_history()

        # Группируем по парам валют и берем последнюю запись для каждой пары
        latest_rates = {}
        for record in sorted(history, key=lambda x: x["timestamp"], reverse=True):
            pair = (record["from_currency"], record["to_currency"])
            if pair not in latest_rates:
                latest_rates[pair] = record["rate"]

        # Преобразуем в формат {валюта: курс} для указанной базовой валюты
        result = {}
        for (from_curr, to_curr), rate in latest_rates.items():
            if from_curr == base_currency:
                result[to_curr] = rate
            elif to_curr == base_currency:
                result[from_curr] = 1.0 / rate

        return result

    def get_rate_history(
        self, from_currency: str, to_currency: str, days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Возвращает историю курса для указанной пары валют.

        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта
            days: Количество дней истории

        Returns:
            Список исторических записей
        """
        history = self._load_history()

        # Фильтруем записи по паре валют
        filtered = [
            record
            for record in history
            if (
                record["from_currency"] == from_currency
                and record["to_currency"] == to_currency
            )
        ]

        # Сортируем по времени и ограничиваем период
        filtered.sort(key=lambda x: x["timestamp"], reverse=True)

        if days > 0:
            cutoff_date = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
            filtered = [
                record
                for record in filtered
                if datetime.fromisoformat(
                    record["timestamp"].replace("Z", "+00:00")
                ).timestamp()
                > cutoff_date  # noqa: E501
            ]

        return filtered

    def cleanup_old_records(self, keep_days: int = 30) -> int:
        """
        Удаляет старые записи из истории.

        Args:
            keep_days: Количество дней для хранения истории

        Returns:
            Количество удаленных записей
        """
        history = self._load_history()

        if not history:
            return 0

        cutoff_timestamp = datetime.utcnow().timestamp() - (keep_days * 24 * 60 * 60)

        initial_count = len(history)
        filtered_history = [
            record
            for record in history
            if datetime.fromisoformat(
                record["timestamp"].replace("Z", "+00:00")
            ).timestamp()
            > cutoff_timestamp  # noqa: E501
        ]

        removed_count = initial_count - len(filtered_history)

        if removed_count > 0:
            self._save_history(filtered_history)

        return removed_count
