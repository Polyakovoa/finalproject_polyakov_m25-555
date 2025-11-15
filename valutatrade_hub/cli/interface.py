import argparse
import sys
from typing import Optional

from prettytable import PrettyTable

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
            description="ValutaTrade Hub - Валютный кошелек"
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
            "show-portfolio", help="Показать портфеле"
        )
        portfolio_parser.add_argument(
            "--base", default="USD", help="Базовая валюта (по умолчанию USD)"
        )

        # buy command
        buy_parser = subparsers.add_parser("buy", help="Купить валюту")
        buy_parser.add_argument(
            "--currency", required=True, help="Код покупаемой валюты"
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
        }

        handler = command_handlers.get(args.command)
        if handler:
            handler(args)
        else:
            print(f"Неизвестная команда: {args.command}")

    def _handle_register(self, args):
        """Обрабатывает команду register."""
        user = self.user_manager.register_user(args.username, args.password)
        print(
            f"Пользователь '{user.username}' зарегистрирован (id={user.user_id}). "
            f"Войдите: login --username {user.username} --password ****"
        )

    def _handle_login(self, args):
        """Обрабатывает команду login."""
        user = self.user_manager.authenticate_user(args.username, args.password)
        self.current_user = {
            "id": user.user_id,
            "username": user.username
        }
        self.session_manager.create_session(user.user_id, user.username)
        print(f"Вы вошли как '{user.username}'")

    def _handle_logout(self, args):
        """Обрабатывает команду logout."""
        if self.current_user:
            username = self.current_user["username"]
            self.current_user = None
            self.session_manager.clear_session()
            print(f"Вы вышли из системы (пользователь: {username})")
        else:
            print("Вы не вошли в систему")

    def _handle_buy(self, args):
        """Обрабатывает команду buy."""
        if not self.current_user:
            raise ValueError("Сначала выполните login")

        if args.amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")

        result = self.trading_service.buy_currency(
            self.current_user["id"],
            args.currency.upper(),
            args.amount
        )

        print(
            f"Покупка выполнена: {args.amount:.4f} {args.currency.upper()} "
            f"по курсу {result['rate']:.2f} USD/{args.currency.upper()}"
        )
        print("Изменения в портфеле:")
        print(
            f"  - {args.currency.upper()}: было {result['old_balance']:.4f} → "
            f"стало {result['new_balance']:.4f}"
        )
        print(f"Оценочная стоимость покупки: {result['total_cost']:,.2f} USD")

    def _handle_sell(self, args):
        """Обрабатывает команду sell."""
        if not self.current_user:
            raise ValueError("Сначала выполните login")

        if args.amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")

        result = self.trading_service.sell_currency(
            self.current_user["id"],
            args.currency.upper(),
            args.amount
        )

        print(
            f"Продажа выполнена: {args.amount:.4f} {args.currency.upper()} "
            f"по курсу {result['rate']:.2f} USD/{args.currency.upper()}"
        )
        print("Изменения в портфеле:")
        print(
            f"  - {args.currency.upper()}: было {result['old_balance']:.4f} → "
            f"стало {result['new_balance']:.4f}"
        )
        print(f"Оценочная выручка: {result['total_income']:,.2f} USD")

    def _handle_get_rate(self, args):
        """Обрабатывает команду get-rate."""
        from_currency = getattr(args, "from_currency").upper()
        to_currency = args.to.upper()

        try:
            rate = self.currency_service.get_exchange_rate(
                from_currency, to_currency
            )

            # Получаем время обновления
            rates_data = self.currency_service._load_rates()
            pair_key = f"{from_currency}_{to_currency}"
            updated_at = rates_data.get(pair_key, {}).get("updated_at")

            if updated_at:
                from datetime import datetime
                dt = datetime.fromisoformat(updated_at)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = "неизвестно"

            print(
                f"Курс {from_currency}→{to_currency}: {rate:.8f} "
                f"(обновлено: {time_str})"
            )

            # Показываем обратный курс
            if from_currency != to_currency:
                reverse_rate = 1.0 / rate
                print(f"Обратный курс {to_currency}→{from_currency}: {reverse_rate:.8f}") # noqa: E501

        except ValueError:
            print(f"Курс {from_currency}→{to_currency} недоступен. Повторите попытку позже.") # noqa: E501

    def _handle_show_portfolio(self, args):
        """Обрабатывает команду show-portfolio."""
        if not self.current_user:
            raise ValueError("Сначала выполните login")

        portfolio = self.user_manager.get_user_portfolio(self.current_user["id"])
        base_currency = args.base.upper()

        # Проверяем валидность базовой валюты
        try:
            total_value = portfolio.get_total_value(base_currency)
        except ValueError:
            raise ValueError(f"Неизвестная базовая валюта '{base_currency}'")

        print(
            f"Портфель пользователя '{self.current_user['username']}' "
            f"(база: {base_currency}):"
        )

        if not portfolio.wallets:
            print("  У вас пока нет кошельков")
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
            except ValueError:
                table.add_row([
                    currency_code,
                    f"{wallet.balance:.4f}",
                    "неизвестно"
                ])

        print(table)
        print(f"{'ИТОГО:':>20} {total_value:,.2f} {base_currency}")


def main():
    """Точка входа для CLI."""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
