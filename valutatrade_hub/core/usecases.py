import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from .models import Portfolio, User


class UserManager:
    """Менеджер для работы с пользователями."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.users_file = self.data_dir / "users.json"
        self.portfolios_file = self.data_dir / "portfolios.json"
        self._ensure_data_files()

    def _ensure_data_files(self) -> None:
        """Создает необходимые файлы данных, если они не существуют."""
        self.data_dir.mkdir(exist_ok=True)

        if not self.users_file.exists():
            self.users_file.write_text('[]', encoding='utf-8')

        if not self.portfolios_file.exists():
            self.portfolios_file.write_text('{}', encoding='utf-8')

    def _load_users(self) -> list:
        """Загружает список пользователей из JSON."""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_users(self, users_data: list) -> None:
        """Сохраняет список пользователей в JSON."""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)

    def _load_portfolios(self) -> dict:
        """Загружает профиль из JSON."""
        try:
            with open(self.portfolios_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_portfolios(self, portfolios_data: dict) -> None:
        """Сохраняет профиль в JSON."""
        with open(self.portfolios_file, 'w', encoding='utf-8') as f:
            json.dump(portfolios_data, f, indent=2, ensure_ascii=False)

    def register_user(self, username: str, password: str) -> User:
        """Регистрирует нового пользователя."""
        if not username or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым")

        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        username = username.strip()
        users_data = self._load_users()

        # Проверяем уникальность username
        for user_data in users_data:
            if user_data["username"] == username:
                raise ValueError(f"Имя пользователя '{username}' уже занято")

        # Генерируем user_id
        if users_data:
            user_id = max(user["user_id"] for user in users_data) + 1
        else:
            user_id = 1

        # Создаем пользователя
        user = User(user_id, username, password)
        users_data.append(user.to_dict())
        self._save_users(users_data)

        # Создаем пустой профиль
        portfolios_data = self._load_portfolios()
        portfolios_data[str(user_id)] = {"wallets": {}}
        self._save_portfolios(portfolios_data)

        return user

    def authenticate_user(self, username: str, password: str) -> User:
        """Аутентифицирует пользователя."""
        if not username or not password:
            raise ValueError("Имя пользователя и пароль обязательны")

        users_data = self._load_users()

        for user_data in users_data:
            if user_data["username"] == username:
                user = User.from_dict(user_data)
                if user.verify_password(password):
                    return user
                else:
                    raise ValueError("Неверный пароль")

        raise ValueError(f"Пользователь '{username}' не найден")

    def get_user_portfolio(self, user_id: int) -> Portfolio:
        """Возвращает профиль пользователя."""
        portfolios_data = self._load_portfolios()
        user_portfolio_data = portfolios_data.get(str(user_id))

        if not user_portfolio_data:
            # Создаем пустой профиль, если не существует
            user_portfolio_data = {"wallets": {}}
            portfolios_data[str(user_id)] = user_portfolio_data
            self._save_portfolios(portfolios_data)

        return Portfolio.from_dict({
            "user_id": user_id,
            "wallets": user_portfolio_data["wallets"]
        })

    def save_user_portfolio(self, portfolio: Portfolio) -> None:
        """Сохраняет профиль пользователя."""
        portfolios_data = self._load_portfolios()
        portfolios_data[str(portfolio.user_id)] = portfolio.to_dict()
        self._save_portfolios(portfolios_data)


class CurrencyService:
    """Сервис для работы с курсами валют."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.rates_file = self.data_dir / "rates.json"
        self._ensure_rates_file()

    def _ensure_rates_file(self) -> None:
        """Создает файл курсов, если он не существует."""
        self.data_dir.mkdir(exist_ok=True)

        if not self.rates_file.exists():
            initial_rates = {
                "USD_USD": {"rate": 1.0, "updated_at": datetime.now().isoformat()},
                "EUR_USD": {"rate": 0.85, "updated_at": datetime.now().isoformat()},
                "GBP_USD": {"rate": 0.73, "updated_at": datetime.now().isoformat()},
                "JPY_USD": {"rate": 110.0, "updated_at": datetime.now().isoformat()},
                "RUB_USD": {"rate": 80.0, "updated_at": datetime.now().isoformat()},
                "BTC_USD": {"rate": 100000.0, "updated_at": datetime.now().isoformat()},
                "ETH_USD": {"rate": 3000.0, "updated_at": datetime.now().isoformat()},
                "source": "stub",
                "last_refresh": datetime.now().isoformat()
            }
            self._save_rates(initial_rates)

    def _load_rates(self) -> dict:
        """Загружает курсы валют из JSON."""
        try:
            with open(self.rates_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_rates(self, rates_data: dict) -> None:
        """Сохраняет курсы валют в JSON."""
        with open(self.rates_file, 'w', encoding='utf-8') as f:
            json.dump(rates_data, f, indent=2, ensure_ascii=False)

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        """Возвращает курс обмена между валютами."""
        if from_currency == to_currency:
            return 1.0

        rates_data = self._load_rates()
        pair_key = f"{from_currency}_{to_currency}"

        # Прямой курс
        if pair_key in rates_data:
            rate_data = rates_data[pair_key]
            # Проверяем свежесть данных (5 минут)
            updated_at = datetime.fromisoformat(rate_data["updated_at"])
            if datetime.now() - updated_at < timedelta(minutes=5):
                return rate_data["rate"]

        # Обратный курс
        reverse_key = f"{to_currency}_{from_currency}"
        if reverse_key in rates_data:
            rate_data = rates_data[reverse_key]
            updated_at = datetime.fromisoformat(rate_data["updated_at"])
            if datetime.now() - updated_at < timedelta(minutes=5):
                return 1.0 / rate_data["rate"]

        # Заглушка для демонстрации
        stub_rates = {
            "USD": 1.0,
            "EUR": 0.85,
            "GBP": 0.73,
            "JPY": 110.0,
            "RUB": 80.0,
            "BTC": 100000.0,
            "ETH": 3000.0
        }

        if from_currency in stub_rates and to_currency in stub_rates:
            return stub_rates[to_currency] / stub_rates[from_currency]

        raise ValueError(f"Курс {from_currency}→{to_currency} недоступен")

    def update_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate: float
    ) -> None:
        """Обновляет курс валюты в кеше."""
        rates_data = self._load_rates()
        pair_key = f"{from_currency}_{to_currency}"

        rates_data[pair_key] = {
            "rate": rate,
            "updated_at": datetime.now().isoformat()
        }
        rates_data["last_refresh"] = datetime.now().isoformat()
        rates_data["source"] = "stub"

        self._save_rates(rates_data)


class TradingService:
    """Сервис для торговых операций."""

    def __init__(self, user_manager: UserManager, currency_service: CurrencyService):
        self.user_manager = user_manager
        self.currency_service = currency_service

    def buy_currency(
        self,
        user_id: int,
        currency: str,
        amount: float
    ) -> Dict[str, Any]:
        """Покупает валюту для пользователя."""
        if amount <= 0:
            raise ValueError("Сумма покупки должна быть положительной")

        portfolio = self.user_manager.get_user_portfolio(user_id)

        # Получаем текущий курс
        try:
            rate = self.currency_service.get_exchange_rate(currency, "USD")
        except ValueError:
            raise ValueError(f"Не удалось получить курс для {currency}→USD")

        # Выполняем покупку
        success = portfolio.buy_currency(currency, amount, rate)
        if not success:
            raise ValueError("Недостаточно средств в USD кошельке")

        # Сохраняем изменения
        self.user_manager.save_user_portfolio(portfolio)

        return {
            "success": True,
            "currency": currency,
            "amount": amount,
            "rate": rate,
            "total_cost": amount * rate,
            "old_balance": portfolio.get_wallet(currency).balance - amount,
            "new_balance": portfolio.get_wallet(currency).balance
        }

    def sell_currency(
        self,
        user_id: int,
        currency: str,
        amount: float
    ) -> Dict[str, Any]:
        """Продает валюту пользователя."""
        if amount <= 0:
            raise ValueError("Сумма продажи должна быть положительной")

        portfolio = self.user_manager.get_user_portfolio(user_id)

        # Проверяем существование кошелька
        wallet = portfolio.get_wallet(currency)
        if not wallet:
            raise ValueError(f"У вас нет кошелька '{currency}'")

        # Проверяем достаточность средств
        if wallet.balance < amount:
            raise ValueError(
                f"Недостаточно средств: доступно {wallet.balance:.4f} {currency}, "
                f"требуется {amount:.4f}"
            )

        # Получаем текущий курс
        try:
            rate = self.currency_service.get_exchange_rate(currency, "USD")
        except ValueError:
            raise ValueError(f"Не удалось получить курс для {currency}→USD")

        # Выполняем продажу
        success = portfolio.sell_currency(currency, amount, rate)
        if not success:
            raise ValueError("Ошибка при выполнении продажи")

        # Сохраняем изменения
        self.user_manager.save_user_portfolio(portfolio)

        return {
            "success": True,
            "currency": currency,
            "amount": amount,
            "rate": rate,
            "total_income": amount * rate,
            "old_balance": wallet.balance + amount,
            "new_balance": wallet.balance
        }

class SessionManager:
    """Менеджер для управления сессиями пользователей."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.session_file = self.data_dir / "session.json"
        self._ensure_session_file()

    def _ensure_session_file(self) -> None:
        """Создает файл сессии, если он не существует."""
        self.data_dir.mkdir(exist_ok=True)
        if not self.session_file.exists():
            self.session_file.write_text('{}', encoding='utf-8')

    def create_session(self, user_id: int, username: str) -> None:
        """Создает сессию для пользователя."""
        session_data = {
            "user_id": user_id,
            "username": username,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
        }
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2)

    def get_current_session(self) -> Dict[str, Any]:
        """Возвращает текущую активную сессию."""
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # Проверяем срок действия сессии
            expires_at = datetime.fromisoformat(session_data["expires_at"])
            if datetime.now() > expires_at:
                self.clear_session()
                return {}

            return session_data
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            return {}

    def clear_session(self) -> None:
        """Очищает текущую сессию."""
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=2)

    def is_session_active(self) -> bool:
        """Проверяет, есть ли активная сессия."""
        return bool(self.get_current_session())
