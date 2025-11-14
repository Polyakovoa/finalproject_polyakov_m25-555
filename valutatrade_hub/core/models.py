import hashlib
from datetime import datetime


class User:
    """Класс пользователя системы валютного кошелька."""

    def __init__(
        self,
        user_id: int,
        username: str,
        password: str,
        salt: str = None,
        registration_date: datetime = None
    ):
        self._user_id = user_id
        self.username = username  # Используем сеттер для проверки
        self._salt = salt or self._generate_salt()
        self._hashed_password = self._hash_password(password)
        self._registration_date = registration_date or datetime.now()

    @property
    def user_id(self) -> int:
        """Геттер для идентификатора пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Геттер для имени пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Сеттер для имени пользователя с проверкой."""
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        if len(value) < 3:
            raise ValueError("Имя пользователя должно быть не короче 3 символов")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        """Геттер для хешированного пароля."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Геттер для соли."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Геттер для даты регистрации."""
        return self._registration_date

    def _generate_salt(self) -> str:
        """Генерирует случайную соль для хеширования пароля."""
        import secrets
        return secrets.token_hex(8)

    def _hash_password(self, password: str) -> str:
        """Хеширует пароль с использованием соли."""
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        password_bytes = password.encode('utf-8')
        salt_bytes = self._salt.encode('utf-8')
        hashed = hashlib.sha256(password_bytes + salt_bytes).hexdigest()
        return hashed

    def verify_password(self, password: str) -> bool:
        """Проверяет введенный пароль на совпадение."""
        try:
            test_hash = self._hash_password(password)
            return test_hash == self._hashed_password
        except ValueError:
            return False

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя."""
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        self._hashed_password = self._hash_password(new_password)

    def get_user_info(self) -> dict:
        """Возвращает информацию о пользователе (без пароля)."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat()
        }

    def to_dict(self) -> dict:
        """Сериализует пользователя в словарь для сохранения в JSON."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Создает объект User из словаря (из JSON)."""
        registration_date = datetime.fromisoformat(data["registration_date"])
        user = cls(
            user_id=data["user_id"],
            username=data["username"],
            password="temp",  # Временный пароль
            salt=data["salt"],
            registration_date=registration_date
        )
        user._hashed_password = data["hashed_password"]
        return user

    def __str__(self) -> str:
        """Строковое представление пользователя."""
        return (f"User(id={self._user_id}, username='{self._username}', "
                f"registered={self._registration_date.strftime('%Y-%m-%d')})")

    def __repr__(self) -> str:
        """Репрезентация объекта для отладки."""
        return (f"User(user_id={self._user_id}, username='{self._username}', "
                f"registration_date='{self._registration_date.isoformat()}')")

class Wallet:
    """Класс кошелька пользователя для конкретной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = currency_code  # Используем сеттер для проверки
        self.balance = balance  # Используем сеттер для проверки

    @property
    def currency_code(self) -> str:
        """Геттер для кода валюты."""
        return self._currency_code

    @currency_code.setter
    def currency_code(self, value: str) -> None:
        """Сеттер для кода валюты с проверкой."""
        if not value or not isinstance(value, str):
            raise ValueError("Код валюты должен быть непустой строкой")
        if len(value) != 3:
            raise ValueError("Код валюты должен состоять из 3 символов")
        self._currency_code = value.upper()

    @property
    def balance(self) -> float:
        """Геттер для баланса кошелька."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Сеттер для баланса с проверкой на отрицательные значения."""
        if not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополняет баланс кошелька."""
        if not isinstance(amount, (int, float)):
            raise ValueError("Сумма пополнения должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")

        self.balance += amount

    def withdraw(self, amount: float) -> bool:
        """Снимает средства с кошелька, если баланс позволяет."""
        if not isinstance(amount, (int, float)):
            raise ValueError("Сумма снятия должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительной")
        if amount > self._balance:
            return False

        self.balance -= amount
        return True

    def get_balance_info(self) -> dict:
        """Возвращает информацию о текущем балансе."""
        return {
            "currency_code": self._currency_code,
            "balance": self._balance
        }

    def to_dict(self) -> dict:
        """Сериализует кошелек в словарь для сохранения в JSON."""
        return {
            "currency_code": self._currency_code,
            "balance": self._balance
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Wallet':
        """Создает объект Wallet из словаря (из JSON)."""
        return cls(
            currency_code=data["currency_code"],
            balance=data["balance"]
        )

    def __str__(self) -> str:
        """Строковое представление кошелька."""
        return f"Wallet({self._currency_code}: {self._balance:.2f})"

    def __repr__(self) -> str:
        """Репрезентация объекта для отладки."""
        return f"Wallet(currency_code='{self._currency_code}', balance={self._balance})"
