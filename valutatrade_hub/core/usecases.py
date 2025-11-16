import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from ..decorators import log_action, measure_time
from ..infra.database import db
from ..infra.settings import settings
from .currencies import CurrencyNotFoundError, get_currency
from .exceptions import ApiRequestError, InsufficientFundsError, TradingError
from .exceptions import CurrencyNotFoundError as CurrencyNotFoundExc
from .models import Portfolio, User

logger = logging.getLogger("valutatrade.usecases")


class UserManager:
    """Менеджер для работы с пользователями."""

    def __init__(self):
        self.data_dir = Path(settings.get("data_dir", "data"))
        self._ensure_data_files()

    def _ensure_data_files(self) -> None:
        """Создает необходимые файлы данных, если они не существуют."""
        if not db.load("users"):
            db.save("users", [])

        portfolios_data = db.load("portfolios")
        if not portfolios_data:
            db.save("portfolios", {})

    def _load_users(self) -> list:
        """Загружает список пользователей из JSON."""
        return db.load("users")

    def _save_users(self, users_data: list) -> None:
        """Сохраняет список пользователей в JSON."""
        db.save("users", users_data)

    def _load_portfolios(self) -> dict:
        """Загружает портфели из JSON."""
        return db.load("portfolios")

    def _save_portfolios(self, portfolios_data: dict) -> None:
        """Сохраняет портфели в JSON."""
        db.save("portfolios", portfolios_data)

    @log_action("REGISTER", verbose=True)
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

        # Создаем портфель с USD кошельком и ПРИВЕТСТВЕННЫМ БОНУСОМ
        portfolios_data = self._load_portfolios()
        WELCOME_BONUS = 300.0  # Приветственный бонус
        portfolios_data[str(user_id)] = {
            "wallets": {
                "USD": {"currency_code": "USD", "balance": WELCOME_BONUS}
            }
        }
        self._save_portfolios(portfolios_data)

        return user

    @log_action("LOGIN", verbose=True)
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
        """Возвращает портфель пользователя."""
        portfolios_data = self._load_portfolios()
        user_portfolio_data = portfolios_data.get(str(user_id))

        if not user_portfolio_data:
            # Создаем портфель с USD кошельком
            user_portfolio_data = {
                "wallets": {
                    "USD": {"currency_code": "USD", "balance": 0.0}
                }
            }
            portfolios_data[str(user_id)] = user_portfolio_data
            self._save_portfolios(portfolios_data)
        elif "wallets" not in user_portfolio_data:
            # Если wallets отсутствует, создаем с USD кошельком
            user_portfolio_data["wallets"] = {
                "USD": {"currency_code": "USD", "balance": 0.0}
            }
            self._save_portfolios(portfolios_data)
        elif "USD" not in user_portfolio_data["wallets"]:
            # Если нет USD кошелька, добавляем его
            user_portfolio_data["wallets"]["USD"] = {"currency_code": "USD", "balance": 0.0} # noqa: E501
            self._save_portfolios(portfolios_data)

        return Portfolio.from_dict({
            "user_id": user_id,
            "wallets": user_portfolio_data["wallets"]
        })

    def save_user_portfolio(self, portfolio: Portfolio) -> None:
        """Сохраняет портфель пользователя."""
        portfolios_data = self._load_portfolios()
        portfolios_data[str(portfolio.user_id)] = portfolio.to_dict()
        self._save_portfolios(portfolios_data)


class CurrencyService:
    """Сервис для работы с курсами валют."""

    def __init__(self):
        # Используем настройки из синглтона
        self.data_dir = Path(settings.get("data_dir", "data"))
        self.rates_ttl = timedelta(seconds=settings.get("rates_ttl_seconds", 300))
        self._ensure_rates_file()

    def _ensure_rates_file(self) -> None:
        """Создает файл курсов, если он не существует."""
        if not db.load("rates"):
            # Создаем новую структуру по умолчанию
            initial_rates = {
                "pairs": {
                    "EUR_USD": {"rate": 0.85, "updated_at": datetime.now().isoformat() + "Z", "source": "stub"}, # noqa: E501
                    "GBP_USD": {"rate": 0.73, "updated_at": datetime.now().isoformat() + "Z", "source": "stub"}, # noqa: E501
                    "JPY_USD": {"rate": 110.0, "updated_at": datetime.now().isoformat() + "Z", "source": "stub"}, # noqa: E501
                    "RUB_USD": {"rate": 80.0, "updated_at": datetime.now().isoformat() + "Z", "source": "stub"}, # noqa: E501
                    "BTC_USD": {"rate": 100000.0, "updated_at": datetime.now().isoformat() + "Z", "source": "stub"}, # noqa: E501
                    "ETH_USD": {"rate": 3000.0, "updated_at": datetime.now().isoformat() + "Z", "source": "stub"}, # noqa: E501
                },
                "last_refresh": datetime.now().isoformat() + "Z",
                "source": "stub"
            }
            db.save("rates", initial_rates)

    def _load_rates(self) -> dict:
        """Загружает курсы валют из JSON."""
        return db.load("rates")

    def _save_rates(self, rates_data: dict) -> None:
        """Сохраняет курсы валют в JSON."""
        db.save("rates", rates_data)

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        """Возвращает курс обмена между валютами."""
        # Валидация кодов валют
        try:
            get_currency(from_currency)
            get_currency(to_currency)
        except CurrencyNotFoundError as e:
            raise CurrencyNotFoundExc(e.code)

        if from_currency == to_currency:
            return 1.0

        # 1. Сначала пробуем получить курс из локального кэша
        cached_rate = self._get_cached_rate(from_currency, to_currency)
        if cached_rate is not None:
            logger.debug(f"Using CACHED rate for {from_currency}->{to_currency}: {cached_rate}") # noqa: E501
            return cached_rate

        # 2. Потом пробуем получить курс из исторических данных Parser Service
        historical_rate = self._get_historical_rate(from_currency, to_currency)
        if historical_rate is not None:
            logger.debug(f"Using HISTORICAL rate for {from_currency}->{to_currency}: {historical_rate}") # noqa: E501
            return historical_rate

        # 3. Или используем заглушку
        try:
            stub_rate = self._get_stub_rate(from_currency, to_currency)
            logger.debug(f"Using STUB rate for {from_currency}->{to_currency}: {stub_rate}") # noqa: E501
            return stub_rate
        except Exception as e:
            raise ApiRequestError(f"Сервис курсов временно недоступен: {e}")

    def _get_cached_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Пытается получить курс из локального кэша rates.json."""
        try:
            rates_data = self._load_rates()

            # Проверяем новую структуру с "pairs"
            if "pairs" in rates_data:
                # Прямая пара (from_to)
                pair_key = f"{from_currency}_{to_currency}"
                if pair_key in rates_data["pairs"]:
                    rate_data = rates_data["pairs"][pair_key]
                    updated_at = datetime.fromisoformat(rate_data["updated_at"].replace('Z', '+00:00')) # noqa: E501
                    if datetime.now().replace(tzinfo=None) - updated_at.replace(tzinfo=None) < self.rates_ttl: # noqa: E501
                        logger.debug(f"Using cached rate from pairs: {pair_key} = {rate_data['rate']}") # noqa: E501
                        return rate_data["rate"]

                # Обратная пара (to_from)
                reverse_key = f"{to_currency}_{from_currency}"
                if reverse_key in rates_data["pairs"]:
                    rate_data = rates_data["pairs"][reverse_key]
                    updated_at = datetime.fromisoformat(rate_data["updated_at"].replace('Z', '+00:00')) # noqa: E501
                    if datetime.now().replace(tzinfo=None) - updated_at.replace(tzinfo=None) < self.rates_ttl: # noqa: E501
                        logger.debug(f"Using cached reverse rate: {reverse_key} = {rate_data['rate']}") # noqa: E501
                        return rate_data["rate"]

            return None

        except Exception as e:
            logger.debug(f"Failed to get cached rate: {e}")
            return None

    def _get_stub_rate(self, from_currency: str, to_currency: str) -> float:
        """Возвращает заглушечный курс (используется как fallback)."""
        stub_rates = {
            "USD": 1.0,
            "EUR": 0.85,
            "GBP": 0.73,
            "JPY": 110.0,
            "RUB": 80.0,
            "BTC": 100000.0,
            "ETH": 3000.0,
            "LTC": 150.0,
            "XRP": 0.5,
            "ADA": 0.4,
            "SOL": 100.0,
            "DOT": 7.0
        }

        if from_currency in stub_rates and to_currency in stub_rates:
            rate = stub_rates[to_currency] / stub_rates[from_currency]
            logger.debug(f"Using stub rate: {from_currency}->{to_currency} = {rate}")
            return rate

        logger.warning(f"No stub rate available for {from_currency}->{to_currency}")
        raise CurrencyNotFoundError(f"{from_currency} или {to_currency}")
    def _get_historical_rate(self, from_currency: str, to_currency: str) -> Optional[float]: # noqa: E501
        """Пытается получить курс из исторических данных Parser Service."""
        try:
            from ..parser_service.storage import RateStorage
            storage = RateStorage()
            latest_rates = storage.get_latest_rates("USD")

            logger.debug(f"Available historical rates: {list(latest_rates.keys())}")

            if from_currency == "USD" and to_currency in latest_rates:
                # USD -> другая валюта: используем прямой курс
                rate = latest_rates[to_currency]
                logger.debug(f"Found USD->{to_currency}: {rate}")
                return rate
            elif to_currency == "USD" and from_currency in latest_rates:
                # Другая валюта -> USD: инвертируем курс
                rate = 1.0 / latest_rates[from_currency]
                logger.debug(f"Found {from_currency}->USD: {rate}")
                return rate
            # Конвертация между двумя не-USD валютами
            elif from_currency in latest_rates and to_currency in latest_rates:
                rate_from_usd = latest_rates[from_currency]  # USD за 1 from_currency
                rate_to_usd = latest_rates[to_currency]      # USD за 1 to_currency
                rate = rate_to_usd / rate_from_usd           # to_currency за 1 from_cu
                logger.debug(f"Calculated {from_currency}->{to_currency}: {rate} (via USD)") # noqa: E501
                return rate

            logger.debug(f"No historical rate found for {from_currency}->{to_currency}")
            return None

        except Exception as e:
            logger.debug(f"Failed to get historical rate for {from_currency}->{to_currency}: {e}") # noqa: E501
            return None

    def get_rate_info(self, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """Возвращает информацию о курсе включая время обновления."""
        rate = self.get_exchange_rate(from_currency, to_currency)
        rates_data = self._load_rates()

        # Ищем время обновления для пары валют в новой структуре
        updated_at = None
        source = "Unknown"

        if "pairs" in rates_data:
            pair_key = f"{from_currency}_{to_currency}"
            reverse_key = f"{to_currency}_{from_currency}"

            if pair_key in rates_data["pairs"]:
                pair_data = rates_data["pairs"][pair_key]
                updated_at = pair_data.get("updated_at")
                source = pair_data.get("source", "Unknown")
            elif reverse_key in rates_data["pairs"]:
                pair_data = rates_data["pairs"][reverse_key]
                updated_at = pair_data.get("updated_at")
                source = pair_data.get("source", "Unknown")

        # Если источник все еще Unknown, определяем по типу валют
        if source == "Unknown":
            try:
                from .currencies import get_currency
                # Проверяем первую валюту в паре
                curr_obj = get_currency(from_currency)
                if hasattr(curr_obj, 'issuing_country'):
                    source = "ExchangeRate-API"
                else:
                    source = "CoinGecko"
            except Exception:
                pass

        if not updated_at:
            updated_at = datetime.now().isoformat() + "Z"

        return {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": rate,
            "updated_at": updated_at,
            "source": source
        }


class TradingService:
    """Сервис для торговых операций."""

    def __init__(self, user_manager: UserManager, currency_service: CurrencyService):
        self.user_manager = user_manager
        self.currency_service = currency_service

    @log_action("BUY", verbose=True)
    @measure_time
    def buy_currency(
        self,
        user_id: int,
        currency: str,
        amount: float
    ) -> Dict[str, Any]:
        """Покупает валюту для пользователя."""
        # Валидация входных данных
        if amount <= 0:
            raise TradingError("Сумма покупки должна быть положительной")

        # Валидация кода валюты
        try:
            currency_obj = get_currency(currency)
        except CurrencyNotFoundError as e:
            raise CurrencyNotFoundExc(e.code)

        portfolio = self.user_manager.get_user_portfolio(user_id)

        # Получаем текущий курс
        try:
            rate = self.currency_service.get_exchange_rate(currency, "USD")
        except (CurrencyNotFoundExc, ApiRequestError) as e:
            raise e
        except Exception as e:
            raise ApiRequestError(f"Не удалось получить курс для {currency}→USD: {e}")

        total_cost = amount * rate

        # Получаем или создаем кошелек целевой валюты
        target_wallet = portfolio.get_wallet(currency)
        old_target_balance = target_wallet.balance if target_wallet else 0.0

        if not target_wallet:
            target_wallet = portfolio.add_currency(currency, 0.0)

        # Получаем USD кошелек
        usd_wallet = portfolio.get_wallet('USD')
        old_usd_balance = usd_wallet.balance if usd_wallet else 0.0

        if not usd_wallet:
            raise TradingError("USD кошелёк не найден")

        # Проверяем достаточно ли средств в USD кошельке
        if usd_wallet.balance < total_cost:
            raise InsufficientFundsError(
                usd_wallet.balance, total_cost, "USD"
            )

        # Выполняем покупку
        try:
            success = portfolio.buy_currency(currency, amount, rate)
            if not success:
                raise TradingError("Не удалось выполнить покупку")
        except Exception as e:
            raise TradingError(f"Ошибка при выполнении покупки: {e}")

        # Сохраняем изменения
        self.user_manager.save_user_portfolio(portfolio)

        return {
            "success": True,
            "currency": currency,
            "currency_name": currency_obj.name,
            "amount": amount,
            "rate": rate,
            "total_cost": total_cost,
            "old_balance": old_target_balance,
            "new_balance": target_wallet.balance,
            "old_usd_balance": old_usd_balance,
            "new_usd_balance": usd_wallet.balance
        }

    @log_action("SELL", verbose=True)
    @measure_time
    def sell_currency(
        self,
        user_id: int,
        currency: str,
        amount: float
    ) -> Dict[str, Any]:
        """Продает валюту пользователя."""
        # Валидация входных данных
        if amount <= 0:
            raise TradingError("Сумма продажи должна быть положительной")

        # Валидация кода валюты
        try:
            currency_obj = get_currency(currency)
        except CurrencyNotFoundError as e:
            raise CurrencyNotFoundExc(e.code)

        portfolio = self.user_manager.get_user_portfolio(user_id)

        # Проверяем существование кошелька
        source_wallet = portfolio.get_wallet(currency)
        if not source_wallet:
            raise TradingError(f"У вас нет кошелька '{currency}'")

        old_source_balance = source_wallet.balance

        # Проверяем достаточность средств
        if source_wallet.balance < amount:
            raise InsufficientFundsError(
                source_wallet.balance, amount, currency
            )

        # Получаем текущий курс
        try:
            rate = self.currency_service.get_exchange_rate(currency, "USD")
        except (CurrencyNotFoundExc, ApiRequestError) as e:
            raise e
        except Exception as e:
            raise ApiRequestError(f"Не удалось получить курс для {currency}→USD: {e}")

        total_income = amount * rate

        # Получаем USD кошелек
        usd_wallet = portfolio.get_wallet('USD')
        old_usd_balance = usd_wallet.balance if usd_wallet else 0.0

        if not usd_wallet:
            usd_wallet = portfolio.add_currency('USD', 0.0)

        # Выполняем продажу
        try:
            success = portfolio.sell_currency(currency, amount, rate)
            if not success:
                raise TradingError("Не удалось выполнить продажу")
        except Exception as e:
            raise TradingError(f"Ошибка при выполнении продажи: {e}")

        # Сохраняем изменения
        self.user_manager.save_user_portfolio(portfolio)

        return {
            "success": True,
            "currency": currency,
            "currency_name": currency_obj.name,
            "amount": amount,
            "rate": rate,
            "total_income": total_income,
            "old_balance": old_source_balance,
            "new_balance": source_wallet.balance,
            "old_usd_balance": old_usd_balance,
            "new_usd_balance": usd_wallet.balance
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

    @log_action("CREATE_SESSION")
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

    @log_action("CLEAR_SESSION")
    def clear_session(self) -> None:
        """Очищает текущую сессию."""
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=2)

    def is_session_active(self) -> bool:
        """Проверяет, есть ли активная сессия."""
        return bool(self.get_current_session())
