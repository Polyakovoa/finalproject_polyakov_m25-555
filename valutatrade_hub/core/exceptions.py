"""Пользовательские исключения для приложения."""


class CurrencyNotFoundError(Exception):
    """Исключение для случая, когда валюта не найдена."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class InsufficientFundsError(Exception):
    """Исключение для случая недостаточных средств."""

    def __init__(self, available: float, required: float, code: str):
        self.available = available
        self.required = required
        self.code = code
        super().__init__(
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )


class InvalidCurrencyError(Exception):
    """Исключение для невалидной валюты."""

    def __init__(self, message: str):
        super().__init__(message)


class TradingError(Exception):
    """Базовое исключение для торговых операций."""

    def __init__(self, message: str):
        super().__init__(message)


class ApiRequestError(Exception):
    """Исключение для ошибок внешнего API."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")


class AuthenticationError(Exception):
    """Исключение для ошибок аутентификации."""

    def __init__(self, message: str):
        super().__init__(message)


class PortfolioError(Exception):
    """Исключение для ошибок работы с портфелем."""

    def __init__(self, message: str):
        super().__init__(message)
