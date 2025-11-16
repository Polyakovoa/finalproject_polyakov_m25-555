"""Модуль для управления JSON-хранилищем с использованием паттерна Singleton."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .settings import settings


class DatabaseManager:
    """
    Менеджер базы данных с гарантией единственного экземпляра (Singleton).

    Обеспечивает абстракцию над JSON-хранилищем с кешированием.
    """

    _instance: Optional['DatabaseManager'] = None
    _initialized: bool = False

    def __new__(cls) -> 'DatabaseManager':
        """Гарантирует создание только одного экземпляра класса."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Инициализирует менеджер базы данных только один раз."""
        if self._initialized:
            return

        self.data_dir = Path(settings.get("data_dir", "data"))
        self._cache: Dict[str, Any] = {}
        self._initialized = True

    def _get_file_path(self, collection: str) -> Path:
        """Возвращает путь к файлу коллекции."""
        return self.data_dir / f"{collection}.json"

    def _read_file(self, file_path: Path) -> Any:
        """Читает данные из файла."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Возвращаем значение по умолчанию в зависимости от ожидаемой структуры
            if "users" in file_path.name:
                return []
            elif "portfolios" in file_path.name:
                return {}
            elif "rates" in file_path.name:
                return {}
            else:
                return None

    def _write_file(self, file_path: Path, data: Any) -> None:
        """Записывает данные в файл."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, collection: str) -> Any:
        """
        Загружает данные из коллекции.

        Args:
            collection: Имя коллекции (без расширения .json)

        Returns:
            Данные коллекции
        """
        if collection in self._cache:
            return self._cache[collection]

        file_path = self._get_file_path(collection)
        data = self._read_file(file_path)
        self._cache[collection] = data
        return data

    def save(self, collection: str, data: Any) -> None:
        """
        Сохраняет данные в коллекцию.

        Args:
            collection: Имя коллекции
            data: Данные для сохранения
        """
        file_path = self._get_file_path(collection)
        self._write_file(file_path, data)
        self._cache[collection] = data

    def clear_cache(self, collection: Optional[str] = None) -> None:
        """
        Очищает кеш.

        Args:
            collection: Если указано, очищает только указанную коллекцию
        """
        if collection:
            self._cache.pop(collection, None)
        else:
            self._cache.clear()

    def get_collection_names(self) -> List[str]:
        """
        Возвращает список доступных коллекций.

        Returns:
            Список имен коллекций
        """
        return [f.stem for f in self.data_dir.glob("*.json")]


# Глобальный экземпляр для удобного импорта
db = DatabaseManager()
