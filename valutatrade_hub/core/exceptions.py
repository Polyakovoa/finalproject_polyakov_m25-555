"""Пользовательские исключения для приложения."""


class CurrencyNotFoundError(Exception):
    """Исключение для случая, когда валюта не найдена."""
    pass


class InsufficientFundsError(Exception):
    """Исключение для случая недостаточных средств."""
    pass


class InvalidCurrencyError(Exception):
    """Исключение для невалидной валюты."""
    pass


class TradingError(Exception):
    """Базовое исключение для торговых операций."""
    pass