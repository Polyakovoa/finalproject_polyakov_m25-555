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
