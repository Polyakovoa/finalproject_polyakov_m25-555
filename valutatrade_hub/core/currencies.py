from abc import ABC, abstractmethod
from typing import Dict
from .exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактный базовый класс для валют."""

    def __init__(self, name: str, code: str):
        self._validate_code(code)
        self._validate_name(name)
        
        self._name = name
        self._code = code.upper()

    def _validate_code(self, code: str) -> None:
        """Валидирует код валюты."""
        if not isinstance(code, str) or not code.strip():
            raise ValueError("Код валюты должен быть непустой строкой")
        if not (2 <= len(code) <= 5):
            raise ValueError("Код валюты должен содержать от 2 до 5 символов")
        if not code.isalnum():
            raise ValueError("Код валюты должен содержать только буквы и цифры")

    def _validate_name(self, name: str) -> None:
        """Валидирует название валюты."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты должно быть непустой строкой")

    @property
    def name(self) -> str:
        """Возвращает человекочитаемое имя валюты."""
        return self._name

    @property
    def code(self) -> str:
        """Возвращает код валюты."""
        return self._code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает строковое представление для UI/логов."""
        pass

    def __str__(self) -> str:
        return self.get_display_info()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self._name}', code='{self._code}')"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Currency):
            return False
        return self._code == other.code

    def __hash__(self) -> int:
        return hash(self._code)


class FiatCurrency(Currency):
    """Класс для фиатных валют."""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self._issuing_country = issuing_country

    @property
    def issuing_country(self) -> str:
        """Возвращает страну/зону эмиссии."""
        return self._issuing_country

    def get_display_info(self) -> str:
        """Возвращает строковое представление фиатной валюты."""
        return f"[FIAT] {self._code} — {self._name} (Issuing: {self._issuing_country})"


class CryptoCurrency(Currency):
    """Класс для криптовалют."""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float = 0.0):
        super().__init__(name, code)
        self._algorithm = algorithm
        self._market_cap = market_cap

    @property
    def algorithm(self) -> str:
        """Возвращает алгоритм консенсуса."""
        return self._algorithm

    @property
    def market_cap(self) -> float:
        """Возвращает рыночную капитализацию."""
        return self._market_cap

    @market_cap.setter
    def market_cap(self, value: float) -> None:
        """Устанавливает рыночную капитализацию."""
        if value < 0:
            raise ValueError("Рыночная капитализация не может быть отрицательной")
        self._market_cap = value

    def get_display_info(self) -> str:
        """Возвращает строковое представление криптовалюты."""
        mcap_str = f"{self._market_cap:.2e}" if self._market_cap > 0 else "N/A"
        return (
            f"[CRYPTO] {self._code} — {self._name} "
            f"(Algo: {self._algorithm}, MCAP: {mcap_str})"
        )


# Реестр валют
_currency_registry: Dict[str, Currency] = {}


def _initialize_currency_registry() -> None:
    """Инициализирует реестр валют предопределенными значениями."""
    global _currency_registry
    
    # Фиатные валюты
    fiats = [
        FiatCurrency("US Dollar", "USD", "United States"),
        FiatCurrency("Euro", "EUR", "Eurozone"),
        FiatCurrency("British Pound", "GBP", "United Kingdom"),
        FiatCurrency("Japanese Yen", "JPY", "Japan"),
        FiatCurrency("Russian Ruble", "RUB", "Russia"),
        FiatCurrency("Swiss Franc", "CHF", "Switzerland"),
        FiatCurrency("Chinese Yuan", "CNY", "China"),
    ]
    
    # Криптовалюты
    cryptos = [
        CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
        CryptoCurrency("Ethereum", "ETH", "Ethash", 4.2e11),
        CryptoCurrency("Litecoin", "LTC", "Scrypt", 6.5e9),
        CryptoCurrency("Ripple", "XRP", "XRP Ledger Consensus", 3.8e10),
        CryptoCurrency("Cardano", "ADA", "Ouroboros", 1.4e10),
    ]
    
    for currency in fiats + cryptos:
        _currency_registry[currency.code] = currency


def get_currency(code: str) -> Currency:
    """Возвращает валюту по коду."""
    if not _currency_registry:
        _initialize_currency_registry()
    
    code_upper = code.upper()
    if code_upper not in _currency_registry:
        raise CurrencyNotFoundError(f"Валюта с кодом '{code}' не найдена")
    
    return _currency_registry[code_upper]


def register_currency(currency: Currency) -> None:
    """Регистрирует новую валюту в реестре."""
    _currency_registry[currency.code] = currency


def get_all_currencies() -> Dict[str, Currency]:
    """Возвращает все зарегистрированные валюты."""
    if not _currency_registry:
        _initialize_currency_registry()
    return _currency_registry.copy()