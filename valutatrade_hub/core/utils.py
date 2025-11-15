"""Вспомогательные функции для работы с валютами."""

from typing import Optional
from .currencies import get_currency, CurrencyNotFoundError
from .exceptions import InvalidCurrencyError


def validate_currency_code(code: str) -> bool:
    """Проверяет валидность кода валюты."""
    try:
        get_currency(code)
        return True
    except CurrencyNotFoundError:
        return False


def normalize_currency_code(code: str) -> str:
    """Нормализует код валюты (приводит к верхнему регистру)."""
    if not isinstance(code, str) or not code.strip():
        raise InvalidCurrencyError("Код валюты должен быть непустой строкой")
    return code.upper().strip()


def get_currency_display_info(code: str) -> Optional[str]:
    """Возвращает информацию о валюте для отображения."""
    try:
        currency = get_currency(code)
        return currency.get_display_info()
    except CurrencyNotFoundError:
        return None


def convert_amount(
    amount: float, 
    from_currency: str, 
    to_currency: str, 
    exchange_rate: float
) -> float:
    """Конвертирует сумму из одной валюты в другую."""
    if amount < 0:
        raise ValueError("Сумма для конвертации не может быть отрицательной")
    if exchange_rate <= 0:
        raise ValueError("Курс обмена должен быть положительным")
    
    return amount * exchange_rate