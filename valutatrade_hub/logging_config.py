"""Конфигурация логирования для приложения."""

import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .infra.settings import settings


class JsonFormatter(logging.Formatter):
    """Форматтер для JSON логов."""

    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись лога в JSON."""
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Добавляем дополнительные поля если они есть
        if hasattr(record, "action_data"):
            log_entry.update(record.action_data)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging() -> None:
    """Настраивает логирование для приложения."""
    log_dir = Path(settings.get("log_dir", "logs"))
    log_dir.mkdir(exist_ok=True)

    log_level = getattr(logging, settings.get("log_level", "INFO").upper())
    log_format = settings.get(
        "log_format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Основной логгер приложения
    logger = logging.getLogger("valutatrade")
    logger.setLevel(log_level)

    # Обработчик для файла (текстовый формат)
    log_file = log_dir / "valutatrade.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)

    # Обработчик для действий (JSON формат)
    actions_file = log_dir / "actions.log"
    actions_handler = logging.handlers.RotatingFileHandler(
        actions_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    actions_handler.setLevel(logging.INFO)
    actions_handler.setFormatter(JsonFormatter())

    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # В консоль только WARNING и выше

    # Форматтер для текстовых логов
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Добавляем обработчики
    logger.addHandler(file_handler)
    logger.addHandler(actions_handler)
    logger.addHandler(console_handler)

    # Специальный логгер для пользовательских операций
    user_ops_logger = logging.getLogger("valutatrade.user_operations")
    user_ops_logger.setLevel(logging.INFO)

    user_ops_file = log_dir / "user_operations.log"
    user_ops_handler = logging.handlers.RotatingFileHandler(
        user_ops_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    user_ops_handler.setFormatter(JsonFormatter())
    user_ops_logger.addHandler(user_ops_handler)

    # Логгер для API запросов
    api_logger = logging.getLogger("valutatrade.api")
    api_logger.setLevel(logging.INFO)

    api_file = log_dir / "api_requests.log"
    api_handler = logging.handlers.RotatingFileHandler(
        api_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    api_handler.setFormatter(formatter)
    api_logger.addHandler(api_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Возвращает логгер с указанным именем.

    Args:
        name: Имя логгера

    Returns:
        Настроенный логгер
    """
    return logging.getLogger(f"valutatrade.{name}")
