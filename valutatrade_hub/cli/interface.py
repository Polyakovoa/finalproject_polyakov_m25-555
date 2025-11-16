import argparse
import sys
from datetime import datetime
from typing import Optional

from prettytable import PrettyTable

from ..core.currencies import get_all_currencies, get_currency
from ..core.exceptions import (
    ApiRequestError,
    AuthenticationError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    TradingError,
)
from ..core.usecases import CurrencyService, SessionManager, TradingService, UserManager


class CLI:
    """Командный интерфейс для валютного кошелька."""

    def __init__(self):
        self.user_manager = UserManager()
        self.currency_service = CurrencyService()
        self.trading_service = TradingService(
            self.user_manager, self.currency_service
        )
        self.session_manager = SessionManager()
        self.current_user: Optional[dict] = None
        self._load_session()

    def _load_session(self):
        """Загружает текущую сессию при инициализации."""
        session_data = self.session_manager.get_current_session()
        if session_data:
            self.current_user = {
                "id": session_data["user_id"],
                "username": session_data["username"]
            }

    def run(self):
        """Запускает CLI интерфейс."""
        parser = argparse.ArgumentParser(
            description="ValutaTrade Hub - Валютный кошелек",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Примеры использования:
  valutatrade register --username alice --password 1234
  valutatrade login --username alice --password 1234
  valutatrade show-portfolio --base EUR
  valutatrade buy --currency BTC --amount 0.1
  valutatrade sell --currency EUR --amount 50
  valutatrade get-rate --from USD --to JPY
  valutatrade logout
            """
        )
        subparsers = parser.add_subparsers(
            dest="command", help="Доступные команды"
        )

        # register command
        register_parser = subparsers.add_parser(
            "register", help="Регистрация нового пользователя"
        )
        register_parser.add_argument(
            "--username", required=True, help="Имя пользователя"
        )
        register_parser.add_argument(
            "--password", required=True, help="Пароль"
        )

        # login command
        login_parser = subparsers.add_parser("login", help="Вход в систему")
        login_parser.add_argument(
            "--username", required=True, help="Имя пользователя"
        )
        login_parser.add_argument(
            "--password", required=True, help="Пароль"
        )

        # logout command
        subparsers.add_parser("logout", help="Выход из системы")

        # show-portfolio command
        portfolio_parser = subparsers.add_parser(
            "show-portfolio", help="Показать портфель"
        )
        portfolio_parser.add_argument(
            "--base", default="USD", help="Базовая валюта (по умолчанию USD)"
        )

        # buy command
        buy_parser = subparsers.add_parser("buy", help="Купить валюту")
        buy_parser.add_argument(
            "--currency", required=True, help="Код покупаемой валюты (например: USD, EUR, BTC)" # noqa: E501
        )
        buy_parser.add_argument(
            "--amount", type=float, required=True,
            help="Количество покупаемой валюты"
        )

        # sell command
        sell_parser = subparsers.add_parser("sell", help="Продать валюту")
        sell_parser.add_argument(
            "--currency", required=True, help="Код продаваемой валюты"
        )
        sell_parser.add_argument(
            "--amount", type=float, required=True,
            help="Количество продаваемой валюты"
        )

        # get-rate command
        rate_parser = subparsers.add_parser(
            "get-rate", help="Получить курс валюты"
        )
        rate_parser.add_argument(
            "--from", required=True, dest="from_currency",
            help="Исходная валюта"
        )
        rate_parser.add_argument(
            "--to", required=True, help="Целевая валюта"
        )

        # list-currencies command
        subparsers.add_parser(
            "list-currencies",
            help="Показать список поддерживаемых валют"
        )

        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            return

        try:
            self._handle_command(args)
        except Exception as e:
            print(f"Ошибка: {e}")
            sys.exit(1)

    def _handle_command(self, args):
        """Обрабатывает команды."""
        command_handlers = {
            "register": self._handle_register,
            "login": self._handle_login,
            "logout": self._handle_logout,
            "show-portfolio": self._handle_show_portfolio,
            "buy": self._handle_buy,
            "sell": self._handle_sell,
            "get-rate": self._handle_get_rate,
            "list-currencies": self._handle_list_currencies,
        }

        try:
            handler = command_handlers.get(args.command)
            if handler:
                handler(args)
            else:
                print(f"Неизвестная команда: {args.command}")
        except InsufficientFundsError as e:
            print(f"❌ Ошибка: {e}")
            print("   Проверьте баланс и попробуйте снова.")
        except CurrencyNotFoundError as e:
            print(f"❌ Ошибка: {e}")
            self._suggest_currency_help()
        except ApiRequestError as e:
            print(f"❌ Ошибка: {e}")
            print("   🔄 Повторите попытку позже или проверьте подключение к сети.")
        except (TradingError, AuthenticationError, ValueError) as e:
            print(f"❌ Ошибка: {e}")
        except Exception as e:
            print(f"💥 Неожиданная ошибка: {e}")
            print("   Пожалуйста, сообщите об этой ошибке разработчикам.")

    def _suggest_currency_help(self):
        """Предлагает помощь по валютам при ошибке CurrencyNotFoundError."""
        print("\n💡 Для просмотра доступных валют используйте: valutatrade list-currencies") # noqa: E501
        print("   Или попробуйте одну из популярных валют: USD, EUR, GBP, BTC, ETH")

    def _handle_register(self, args):
        """Обрабатывает команду register."""
        user = self.user_manager.register_user(args.username, args.password)
        print(f"✅ Пользователь '{user.username}' зарегистрирован (id={user.user_id}).")
        print(f"   🔑 Войдите в систему: valutatrade login --username {user.username} --password ****") # noqa: E501

    def _handle_login(self, args):
        """Обрабатывает команду login."""
        user = self.user_manager.authenticate_user(args.username, args.password)
        self.current_user = {
            "id": user.user_id,
            "username": user.username
        }
        self.session_manager.create_session(user.user_id, user.username)
        print(f"✅ Вы вошли как '{user.username}'")

    def _handle_logout(self, args):
        """Обрабатывает команду logout."""
        if self.current_user:
            username = self.current_user["username"]
            self.current_user = None
            self.session_manager.clear_session()
            print(f"✅ Вы вышли из системы (пользователь: {username})")
        else:
            print("ℹ️  Вы не вошли в систему")

    def _handle_show_portfolio(self, args):
        """Обрабатывает команду show-portfolio."""
        if not self.current_user:
            raise AuthenticationError("Сначала выполните login")

        portfolio = self.user_manager.get_user_portfolio(self.current_user["id"])
        base_currency = args.base.upper()

        # Проверяем валидность базовой валюты
        try:
            get_currency(base_currency)
            total_value = portfolio.get_total_value(base_currency)
        except CurrencyNotFoundError:
            raise CurrencyNotFoundError(base_currency)

        print(
            f"📊 Портфель пользователя '{self.current_user['username']}' "
            f"(база: {base_currency}):"
        )

        if not portfolio.wallets:
            print("   💼 У вас пока нет кошельков")
            return

        table = PrettyTable()
        table.field_names = ["Валюта", "Баланс", f"Стоимость ({base_currency})"]
        table.align = "r"
        table.align["Валюта"] = "l"

        for currency_code, wallet in portfolio.wallets.items():
            try:
                if currency_code == base_currency:
                    value = wallet.balance
                else:
                    rate = self.currency_service.get_exchange_rate(
                        currency_code, base_currency
                    )
                    value = wallet.balance * rate

                table.add_row([
                    currency_code,
                    f"{wallet.balance:.4f}",
                    f"{value:.2f}"
                ])
            except (CurrencyNotFoundError, ApiRequestError):
                table.add_row([
                    currency_code,
                    f"{wallet.balance:.4f}",
                    "неизвестно"
                ])

        print(table)
        print(f"{'💰 ИТОГО:':>20} {total_value:,.2f} {base_currency}")

    def _handle_buy(self, args):
        """Обрабатывает команду buy."""
        if not self.current_user:
            raise AuthenticationError("Сначала выполните login")

        if args.amount <= 0:
            raise TradingError("Сумма покупки должна быть положительной")

        try:
            result = self.trading_service.buy_currency(
                self.current_user["id"],
                args.currency.upper(),
                args.amount
            )

            print("✅ Покупка выполнена успешно!")
            print(f"   💰 Куплено: {result['amount']:.4f} {result['currency']} ({result['currency_name']})") # noqa: E501
            print(f"   📈 Курс: {result['rate']:.4f} USD/{result['currency']}")
            print(f"   💵 Стоимость: {result['total_cost']:,.2f} USD")
            print("   📊 Изменения баланса:")
            print(f"      - {result['currency']}: {result['old_balance']:.4f} → {result['new_balance']:.4f}") # noqa: E501
            print(f"      - USD: {result['old_usd_balance']:.2f} → {result['new_usd_balance']:.2f}") # noqa: E501

        except CurrencyNotFoundError:
            raise CurrencyNotFoundError(args.currency.upper())
        except ApiRequestError as e:
            raise e

    def _handle_sell(self, args):
        """Обрабатывает команду sell."""
        if not self.current_user:
            raise AuthenticationError("Сначала выполните login")

        if args.amount <= 0:
            raise TradingError("Сумма продажи должна быть положительной")

        try:
            result = self.trading_service.sell_currency(
                self.current_user["id"],
                args.currency.upper(),
                args.amount
            )

            print("✅ Продажа выполнена успешно!")
            print(f"   💰 Продано: {result['amount']:.4f} {result['currency']} ({result['currency_name']})") # noqa: E501
            print(f"   📈 Курс: {result['rate']:.4f} USD/{result['currency']}")
            print(f"   💵 Выручка: {result['total_income']:,.2f} USD")
            print("   📊 Изменения баланса:")
            print(f"      - {result['currency']}: {result['old_balance']:.4f} → {result['new_balance']:.4f}") # noqa: E501
            print(f"      - USD: {result['old_usd_balance']:.2f} → {result['new_usd_balance']:.2f}") # noqa: E501

        except CurrencyNotFoundError:
            raise CurrencyNotFoundError(args.currency.upper())
        except ApiRequestError as e:
            raise e

    def _handle_get_rate(self, args):
        """Обрабатывает команду get-rate."""
        from_currency = getattr(args, "from_currency").upper()
        to_currency = args.to.upper()

        try:
            rate_info = self.currency_service.get_rate_info(from_currency, to_currency)

            dt = datetime.fromisoformat(rate_info["updated_at"])
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

            print("📈 Курс обмена:")
            print(f"   {from_currency} → {to_currency}: {rate_info['rate']:.8f}")
            print(f"   🕒 Обновлено: {time_str}")

            # Показываем обратный курс
            if from_currency != to_currency:
                reverse_rate = 1.0 / rate_info['rate']
                print(f"   {to_currency} → {from_currency}: {reverse_rate:.8f}")

        except CurrencyNotFoundError as e:
            raise e
        except ApiRequestError as e:
            raise e

    def _handle_list_currencies(self, args):
        """Обрабатывает команду list-currencies."""
        currencies = get_all_currencies()

        table = PrettyTable()
        table.field_names = ["Код", "Тип", "Название", "Доп. информация"]
        table.align = "l"

        for code, currency in currencies.items():
            currency_type = "FIAT" if hasattr(currency, 'issuing_country') else "CRYPTO"

            if currency_type == "FIAT":
                extra_info = f"Страна: {currency.issuing_country}"
            else:
                extra_info = f"Алгоритм: {currency.algorithm}"

            table.add_row([
                code,
                currency_type,
                currency.name,
                extra_info
            ])

        print("📋 Поддерживаемые валюты:")
        print(table)
        print(f"Всего: {len(currencies)} валют")


def main():
    """Точка входа для CLI."""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
