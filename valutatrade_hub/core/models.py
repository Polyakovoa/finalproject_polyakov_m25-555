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

class Portfolio:
    """Класс для управления всеми кошельками одного пользователя."""

    def __init__(self, user_id: int, wallets: dict[str, Wallet] = None):
        self._user_id = user_id
        self._wallets = wallets or {}

    @property
    def user_id(self) -> int:
        """Геттер для идентификатора пользователя."""
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Геттер для копии словаря кошельков."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str, initial_balance: float = 0.0) -> Wallet:
        """Добавляет новый кошелёк в портфель, если его ещё нет."""
        if not currency_code or not isinstance(currency_code, str):
            raise ValueError("Код валюты должен быть непустой строкой")
        
        currency_code = currency_code.upper()
        if currency_code in self._wallets:
            raise ValueError(f"Кошелёк с валютой {currency_code} уже существует")
        
        wallet = Wallet(currency_code, initial_balance)
        self._wallets[currency_code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает объект Wallet по коду валюты."""
        currency_code = currency_code.upper()
        return self._wallets.get(currency_code)

    def get_total_value(self, base_currency: str = 'USD') -> float:
        """Возвращает общую стоимость всех валют в указанной базовой валюте."""
        # Фиксированные курсы для демонстрации
        exchange_rates = {
            'USD': 1.0,
            'EUR': 0.85,
            'GBP': 0.73,
            'JPY': 110.0,
            'RUB': 80.0,
            'BTC': 100000.0,  # 1 BTC = 100000 USD
            'ETH': 3000.0    # 1 ETH = 3000 USD
        }
        
        if base_currency not in exchange_rates:
            raise ValueError(f"Неизвестная базовая валюта: {base_currency}")
        
        total_value = 0.0
        
        for currency_code, wallet in self._wallets.items():
            if currency_code not in exchange_rates:
                print(f"Предупреждение: неизвестный курс для валюты {currency_code}")
                continue
            
            # Конвертируем в базовую валюту
            if currency_code == base_currency:
                total_value += wallet.balance
            else:
                # Сначала конвертируем в USD, затем в базовую валюту
                value_in_usd = wallet.balance * exchange_rates[currency_code]
                if base_currency != 'USD':
                    value_in_base = value_in_usd / exchange_rates[base_currency]
                else:
                    value_in_base = value_in_usd
                total_value += value_in_base
        
        return round(total_value, 2)

    def buy_currency(
        self, 
        target_currency: str, 
        amount: float, 
        price: float
    ) -> bool:
        """Покупает валюту, списывая сумму с USD-кошелька."""
        if amount <= 0:
            raise ValueError("Сумма покупки должна быть положительной")
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        
        total_cost = amount * price
        
        # Получаем или создаем кошелек целевой валюты
        target_wallet = self.get_wallet(target_currency)
        if not target_wallet:
            target_wallet = self.add_currency(target_currency)
        
        # Получаем USD кошелек
        usd_wallet = self.get_wallet('USD')
        if not usd_wallet:
            raise ValueError("USD кошелёк не найден для совершения покупки")
        
        # Проверяем достаточно ли средств в USD кошельке
        if usd_wallet.balance < total_cost:
            return False
        
        # Списываем с USD кошелька и пополняем целевой кошелек
        if usd_wallet.withdraw(total_cost):
            target_wallet.deposit(amount)
            return True
        
        return False

    def sell_currency(
        self, 
        source_currency: str, 
        amount: float, 
        price: float
    ) -> bool:
        """Продает валюту, начисляя сумму на USD-кошелёк."""
        if amount <= 0:
            raise ValueError("Сумма продажи должна быть положительной")
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        
        total_income = amount * price
        
        # Получаем кошелек исходной валюты
        source_wallet = self.get_wallet(source_currency)
        if not source_wallet:
            raise ValueError(f"Кошелёк {source_currency} не найден")
        
        # Получаем или создаем USD кошелек
        usd_wallet = self.get_wallet('USD')
        if not usd_wallet:
            usd_wallet = self.add_currency('USD')
        
        # Проверяем достаточно ли средств в исходном кошельке
        if source_wallet.balance < amount:
            return False
        
        # Списываем с исходного кошелька и пополняем USD кошелек
        if source_wallet.withdraw(amount):
            usd_wallet.deposit(total_income)
            return True
        
        return False

    def to_dict(self) -> dict:
        """Сериализует портфель в словарь для сохранения в JSON."""
        wallets_dict = {}
        for currency_code, wallet in self._wallets.items():
            wallets_dict[currency_code] = wallet.to_dict()
        
        return {
            "user_id": self._user_id,
            "wallets": wallets_dict
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Portfolio':
        """Создает объект Portfolio из словаря (из JSON)."""
        wallets = {}
        for currency_code, wallet_data in data["wallets"].items():
            wallets[currency_code] = Wallet.from_dict(wallet_data)
        
        return cls(user_id=data["user_id"], wallets=wallets)

    def __str__(self) -> str:
        """Строковое представление портфеля."""
        wallet_count = len(self._wallets)
        total_value = self.get_total_value('USD')
        return (f"Portfolio(user_id={self._user_id}, wallets={wallet_count}, "
                f"total_value={total_value:.2f} USD)")

    def __repr__(self) -> str:
        """Репрезентация объекта для отладки."""
        return (f"Portfolio(user_id={self._user_id}, "
                f"wallets={list(self._wallets.keys())})")