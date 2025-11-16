"""Модуль для управления настройками приложения с использованием паттерна Singleton."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import toml


class SettingsLoader:
    """
    Загрузчик настроек приложения с гарантией единственного экземпляра (Singleton).

    Реализация через __new__ выбрана для простоты и читабельности,
    а также для совместимости с наследованием при необходимости.
    """

    _instance: Optional['SettingsLoader'] = None
    _initialized: bool = False

    def __new__(cls) -> 'SettingsLoader':
        """Гарантирует создание только одного экземпляра класса."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Инициализирует настройки только один раз."""
        if self._initialized:
            return

        self._config: Dict[str, Any] = {}
        self._load_configuration()
        self._initialized = True

    def _load_configuration(self) -> None:
        """Загружает конфигурацию из различных источников."""
        # Базовые настройки по умолчанию
        default_config = {
            "data_dir": "data",
            "rates_ttl_seconds": 300,  # 5 минут
            "default_base_currency": "USD",
            "log_dir": "logs",
            "log_level": "INFO",
            "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "log_rotation": "10 MB",
            "log_retention": "7 days",
            "supported_currencies": ["USD", "EUR", "GBP", "JPY", "RUB", "BTC", "ETH"],
            "session_timeout_hours": 24,
            "max_login_attempts": 3,
            "api_timeout_seconds": 30,
            "exchangerate_api_key": "4b468e05030488a5d11e381c",
            "coingecko_api_key": "",
            "rates_update_interval": 300,
            "api_max_retries": 3,
            "api_retry_delay": 1.0,
        }

        # Загружаем из pyproject.toml если существует
        pyproject_path = Path("pyproject.toml")
        if pyproject_path.exists():
            try:
                pyproject_config = toml.load(pyproject_path)
                valutatrade_config = pyproject_config.get("tool", {}).get("valutatrade", {}) # noqa: E501
                default_config.update(valutatrade_config)
            except Exception as e:
                print(f"Warning: Could not load pyproject.toml: {e}")

        # Загружаем из config.json если существует
        config_json_path = Path("config.json")
        if config_json_path.exists():
            try:
                with open(config_json_path, 'r', encoding='utf-8') as f:
                    json_config = json.load(f)
                default_config.update(json_config)
            except Exception as e:
                print(f"Warning: Could not load config.json: {e}")

        # Переопределяем переменными окружения
        env_mapping = {
            "VALUTATRADE_DATA_DIR": "data_dir",
            "VALUTATRADE_RATES_TTL": "rates_ttl_seconds",
            "VALUTATRADE_BASE_CURRENCY": "default_base_currency",
            "VALUTATRADE_LOG_LEVEL": "log_level",
            "VALUTATRADE_SESSION_TIMEOUT": "session_timeout_hours"
        }

        for env_var, config_key in env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Преобразуем типы данных
                if config_key in ["rates_ttl_seconds", "session_timeout_hours", "max_login_attempts", "api_timeout_seconds"]: # noqa: E501
                    try:
                        default_config[config_key] = int(env_value)
                    except ValueError:
                        print(f"Warning: Invalid integer value for {env_var}: {env_value}") # noqa: E501
                else:
                    default_config[config_key] = env_value

        self._config = default_config

        # Создаем необходимые директории
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Создает необходимые директории, если они не существуют."""
        directories = [
            self.get("data_dir"),
            self.get("log_dir")
        ]

        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Возвращает значение настройки по ключу.

        Args:
            key: Ключ настройки
            default: Значение по умолчанию, если ключ не найден

        Returns:
            Значение настройки или default
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Устанавливает значение настройки (только в runtime).

        Args:
            key: Ключ настройки
            value: Новое значение
        """
        self._config[key] = value

    def reload(self) -> None:
        """Перезагружает конфигурацию из файлов."""
        self._initialized = False
        self.__init__()

    def get_all(self) -> Dict[str, Any]:
        """
        Возвращает все текущие настройки.

        Returns:
            Словарь со всеми настройками
        """
        return self._config.copy()

    def __getitem__(self, key: str) -> Any:
        """Позволяет использовать доступ по ключу как к словарю."""
        return self.get(key)

    def __contains__(self, key: str) -> bool:
        """Проверяет наличие ключа в настройках."""
        return key in self._config


# Глобальный экземпляр для удобного импорта
settings = SettingsLoader()
