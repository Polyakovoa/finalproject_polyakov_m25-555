"""Декораторы для расширения функциональности приложения."""

import functools
import logging
import time
from typing import Any, Callable, Dict, Optional

from .logging_config import get_logger


def log_action(
    action_name: Optional[str] = None, level: str = "INFO", verbose: bool = False
):  # noqa: E501
    """
    Декоратор для логирования доменных операций.

    Args:
        action_name: Название действия (если None, используется имя функции)
        level: Уровень логирования (INFO, DEBUG, WARNING, ERROR)
        verbose: Подробное логирование с контекстом
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = get_logger("user_operations")
            action = action_name or func.__name__.upper()

            # Собираем базовую информацию для лога
            log_data: Dict[str, Any] = {
                "action": action,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }

            # Извлекаем информацию о пользователе из аргументов
            user_info = _extract_user_info(args, kwargs)
            if user_info:
                log_data.update(user_info)

            # Извлекаем информацию о валюте и сумме
            currency_info = _extract_currency_info(args, kwargs, action)
            if currency_info:
                log_data.update(currency_info)

            try:
                # Выполняем функцию
                result = func(*args, **kwargs)

                # Добавляем информацию о результате
                log_data.update({"result": "OK", "status": "success"})

                # Если verbose режим и есть результат, добавляем детали
                if verbose and result and isinstance(result, dict):
                    log_data.update(_extract_verbose_info(result, action))

                # Логируем успешное выполнение
                _log_action_data(logger, level, log_data)

                return result

            except Exception as e:
                # Логируем ошибку
                log_data.update(
                    {
                        "result": "ERROR",
                        "status": "failed",
                        "error_type": e.__class__.__name__,
                        "error_message": str(e),
                    }
                )

                _log_action_data(logger, "ERROR", log_data)
                raise

        return wrapper

    return decorator


def _extract_user_info(args: tuple, kwargs: dict) -> Dict[str, Any]:
    """Извлекает информацию о пользователе из аргументов."""
    user_info = {}

    # Пытаемся найти user_id в аргументах
    for arg in args:
        if isinstance(arg, int) and arg > 0:
            user_info["user_id"] = arg
            break

    # Ищем в ключевых аргументах
    if "user_id" in kwargs:
        user_info["user_id"] = kwargs["user_id"]
    if "username" in kwargs:
        user_info["username"] = kwargs["username"]

    return user_info


def _extract_currency_info(args: tuple, kwargs: dict, action: str) -> Dict[str, Any]:
    """Извлекает информацию о валюте и сумме из аргументов."""
    currency_info = {}

    # Для торговых операций
    if action in ["BUY", "SELL"]:
        if "currency" in kwargs:
            currency_info["currency_code"] = kwargs["currency"]
        if "amount" in kwargs:
            currency_info["amount"] = float(kwargs["amount"])

        # Ищем в позиционных аргументах
        for i, arg in enumerate(args):
            if isinstance(arg, str) and len(arg) in [3, 4] and arg.isupper():
                currency_info["currency_code"] = arg
            elif isinstance(arg, (int, float)) and arg > 0:
                currency_info["amount"] = float(arg)

    # Для операций с курсами
    elif action in ["GET_RATE", "EXCHANGE_RATE"]:
        if "from_currency" in kwargs:
            currency_info["from_currency"] = kwargs["from_currency"]
        if "to_currency" in kwargs:
            currency_info["to_currency"] = kwargs["to_currency"]

    return currency_info


def _extract_verbose_info(result: Dict[str, Any], action: str) -> Dict[str, Any]:
    """Извлекает подробную информацию из результата функции."""
    verbose_info = {}

    if action == "BUY":
        verbose_info.update(
            {
                "rate": result.get("rate"),
                "total_cost": result.get("total_cost"),
                "old_balance": result.get("old_balance"),
                "new_balance": result.get("new_balance"),
                "base_currency": "USD",
            }
        )
    elif action == "SELL":
        verbose_info.update(
            {
                "rate": result.get("rate"),
                "total_income": result.get("total_income"),
                "old_balance": result.get("old_balance"),
                "new_balance": result.get("new_balance"),
                "base_currency": "USD",
            }
        )
    elif action == "GET_RATE":
        verbose_info.update(
            {
                "rate": result.get("rate"),
                "from_currency": result.get("from_currency"),
                "to_currency": result.get("to_currency"),
            }
        )

    return verbose_info


def _log_action_data(
    logger: logging.Logger, level: str, log_data: Dict[str, Any]
) -> None:  # noqa: E501
    """Логирует данные действия с указанным уровнем."""
    log_method = getattr(logger, level.lower())

    # Создаем LogRecord с дополнительными данными
    extra_data = {"action_data": log_data}
    log_method(log_data["action"], extra=extra_data)


def measure_time(func: Callable) -> Callable:
    """Декоратор для измерения времени выполнения функции."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        logger = get_logger("performance")
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.debug(
                f"Функция {func.__name__} выполнена за {execution_time:.4f} секунд"
            )  # noqa: E501

    return wrapper


def require_login(func: Callable) -> Callable:
    """Декоратор для проверки аутентификации пользователя."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> Any:
        if not hasattr(self, "current_user") or not self.current_user:
            from .core.exceptions import AuthenticationError

            raise AuthenticationError("Сначала выполните login")
        return func(self, *args, **kwargs)

    return wrapper


def cache_result(ttl_seconds: int = 300):
    """Декоратор для кеширования результатов функций."""

    def decorator(func: Callable) -> Callable:
        cache = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            cache_key = str(args) + str(sorted(kwargs.items()))
            current_time = time.time()

            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if current_time - timestamp < ttl_seconds:
                    get_logger("cache").debug(f"Кеш попадание для {func.__name__}")
                    return result

            result = func(*args, **kwargs)
            cache[cache_key] = (result, current_time)
            get_logger("cache").debug(f"Кеш обновлен для {func.__name__}")
            return result

        def clear_cache():
            cache.clear()
            get_logger("cache").info(f"Кеш очищен для {func.__name__}")

        wrapper.clear_cache = clear_cache
        return wrapper

    return decorator


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """Декоратор для повторения вызовов при ошибках."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = get_logger("retry")
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Попытка {attempt + 1}/{max_attempts} не удалась для {func.__name__}: {e}"  # noqa: E501
                    )

                    if attempt < max_attempts - 1:
                        time.sleep(delay * (attempt + 1))

            logger.error(f"Все {max_attempts} попыток не удались для {func.__name__}")
            raise last_exception

        return wrapper

    return decorator
