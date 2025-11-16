import argparse
import json
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
from ..infra.database import db
from ..parser_service.updater import RatesUpdater


class CLI:
    """Командный интерфейс для валютного кошелька."""

    def __init__(self):
        self.user_manager = UserManager()
        self.currency_service = CurrencyService()
        self.trading_service = TradingService(self.user_manager, self.currency_service)
        self.session_manager = SessionManager()
        self.current_user: Optional[dict] = None
        self._load_session()

    def _load_session(self):
        """Загружает текущую сессию при инициализации."""
        session_data = self.session_manager.get_current_session()
        if session_data:
            self.current_user = {
                "id": session_data["user_id"],
                "username": session_data["username"],
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
  valutatrade show-rates --top 5
  valutatrade update-rates --source coingecko
  valutatrade logout
            """,
        )
        subparsers = parser.add_subparsers(dest="command", help="Доступные команды")

        # register command
        register_parser = subparsers.add_parser(
            "register", help="Регистрация нового пользователя"
        )
        register_parser.add_argument(
            "--username", required=True, help="Имя пользователя"
        )
        register_parser.add_argument("--password", required=True, help="Пароль")

        # login command
        login_parser = subparsers.add_parser("login", help="Вход в систему")
        login_parser.add_argument("--username", required=True, help="Имя пользователя")
        login_parser.add_argument("--password", required=True, help="Пароль")

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
            "--currency",
            required=True,
            help="Код покупаемой валюты (например: USD, EUR, BTC)", # noqa: E501
        )
        buy_parser.add_argument(
            "--amount", type=float, required=True, help="Количество покупаемой валюты"
        )

        # sell command
        sell_parser = subparsers.add_parser("sell", help="Продать валюту")
        sell_parser.add_argument(
            "--currency", required=True, help="Код продаваемой валюты"
        )
        sell_parser.add_argument(
            "--amount", type=float, required=True, help="Количество продаваемой валюты"
        )

        # get-rate command
        rate_parser = subparsers.add_parser("get-rate", help="Получить курс валюты")
        rate_parser.add_argument(
            "--from", required=True, dest="from_currency", help="Исходная валюта"
        )
        rate_parser.add_argument("--to", required=True, help="Целевая валюта")

        # list-currencies command
        subparsers.add_parser(
            "list-currencies", help="Показать список поддерживаемых валют"
        )

        # update-rates command
        update_parser = subparsers.add_parser(
            "update-rates", help="Обновить курсы валют из внешних API"
        )
        update_parser.add_argument(
            "--source",
            choices=["coingecko", "exchangerate", "all"],
            default="all",
            help="Источник данных (coingecko, exchangerate, all)",
        )

        # show-rates command
        show_rates_parser = subparsers.add_parser(
            "show-rates", help="Показать актуальные курсы из локального кэша"
        )
        show_rates_parser.add_argument(
            "--currency", help="Показать курс только для указанной валюты"
        )
        show_rates_parser.add_argument(
            "--top", type=int, help="Показать N самых дорогих криптовалют"
        )
        show_rates_parser.add_argument(
            "--base", default="USD", help="Базовая валюта для отображения курсов"
        )

        # add-funds command
        funds_parser = subparsers.add_parser(
            "add-funds", help="Пополнить баланс (только для USD)"
        )
        funds_parser.add_argument(
            "--amount", type=float, required=True, help="Сумма пополнения в USD"
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

    def _handle_add_funds(self, args):
        """Обрабатывает команду add-funds."""
        if not self.current_user:
            raise AuthenticationError("Сначала выполните login")

        if args.amount <= 0:
            raise TradingError("Сумма пополнения должна быть положительной")

        user_id = self.current_user["id"]
        portfolio = self.user_manager.get_user_portfolio(user_id)

        # Получаем или создаем USD кошелек
        usd_wallet = portfolio.get_wallet("USD")
        if not usd_wallet:
            usd_wallet = portfolio.add_currency("USD", 0.0)

        old_balance = usd_wallet.balance
        new_balance = old_balance + args.amount

        # Пополняем баланс
        usd_wallet.balance = new_balance
        self.user_manager.save_user_portfolio(portfolio)

        print("✅ Баланс успешно пополнен!")
        print(f"   💰 Пополнено: {args.amount:.2f} USD")
        print(f"   📊 Баланс USD: {old_balance:.2f} → {new_balance:.2f}")

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
            "update-rates": self._handle_update_rates,
            "show-rates": self._handle_show_rates,
            "add-funds": self._handle_add_funds,
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

    def _handle_update_rates(self, args):
        """Обрабатывает команду update-rates с фильтрацией по источникам."""
        print("🔄 Обновление курсов валют...")

        try:
            updater = RatesUpdater()

            # Логируем выбранный источник
            if args.source != "all":
                print(f"📡 Источник: {args.source}")

            # Выполняем обновление
            stats = updater.run_update()

            if stats["total_updated"] > 0:
                print("✅ Курсы обновлены успешно!")
                print(f"   📊 Обновлено пар: {stats['total_updated']}")
                print(f"   💵 Фиатные валюты: {stats.get('fiat_rates', 0)}")
                print(f"   ₿ Криптовалюты: {stats.get('crypto_rates', 0)}")
                print(f"   ⚠️ Ошибки: {stats.get('errors', 0)}")

                # Показываем детали по источникам
                if "details" in stats and "sources" in stats["details"]:
                    for source, source_stats in stats["details"]["sources"].items():
                        status_icon = (
                            "✅" if source_stats["status"] == "success" else "❌"
                        )
                        print(
                            f"   {status_icon} {source}: {source_stats.get('pairs_count', 0)} пар" # noqa: E501
                        )
            else:
                print("ℹ️  Новые курсы не получены (возможно, временные проблемы с API)")

        except ApiRequestError as e:
            print(f"❌ Ошибка API: {e}")
            print("   🔄 Проверьте подключение к интернету и повторите попытку позже.")
        except Exception as e:
            print(f"❌ Ошибка при обновлении курсов: {e}")

    def _handle_show_rates(self, args):
        """Обрабатывает команду show-rates с фильтрацией."""
        try:
            # Загружаем данные из кэша
            cache_data = db.load("rates")

            if not cache_data or "pairs" not in cache_data or not cache_data["pairs"]:
                print("❌ Локальный кэш курсов пуст.")
                print(
                    "   💡 Выполните 'valutatrade update-rates', чтобы загрузить данные." # noqa: E501
                )
                return

            pairs = cache_data["pairs"]
            last_refresh = cache_data.get("last_refresh", "неизвестно")

            # Форматируем время обновления
            try:
                dt = datetime.fromisoformat(last_refresh.replace("Z", "+00:00"))
                refresh_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except Exception:
                refresh_str = last_refresh

            print(f"📈 Курсы из кэша (обновлено: {refresh_str})")
            print()

            # Применяем фильтры
            filtered_pairs = self._filter_rates(pairs, args)

            if not filtered_pairs:
                print("❌ Нет данных, соответствующих указанным фильтрам.")
                return

            # Сортируем и выводим
            self._display_rates_table(filtered_pairs, args)

        except FileNotFoundError:
            print("❌ Файл кэша курсов не найден.")
            print("💡 Выполните 'valutatrade update-rates', чтобы загрузить данные.")
        except json.JSONDecodeError:
            print("❌ Ошибка чтения файла кэша.")
            print(
                "💡 Выполните 'valutatrade update-rates', чтобы перезагрузить данные."
            )

    def _filter_rates(self, pairs: dict, args) -> list:
        """Применяет фильтры к списку курсов."""
        filtered = []
        target_base = args.base.upper()

        for pair_key, rate_data in pairs.items():
            from_currency, to_currency = pair_key.split("_")

            # Фильтр по валюте
            if args.currency:
                currency_upper = args.currency.upper()
                if from_currency != currency_upper:
                    continue

            # Если базовая валюта USD - показываем как есть
            if target_base == "USD":
                filtered.append((pair_key, rate_data))
            else:
                # Для других базовых валют нужна конвертация
                if to_currency == "USD" and from_currency != target_base:
                    # Пытаемся найти курс USD к целевой базе
                    usd_to_base_pair = f"USD_{target_base}"
                    base_to_usd_pair = f"{target_base}_USD"

                    if usd_to_base_pair in pairs:
                        # Прямой курс найден
                        usd_to_base_rate = pairs[usd_to_base_pair]["rate"]
                        converted_rate = rate_data["rate"] * usd_to_base_rate
                        converted_pair = f"{from_currency}_{target_base}"
                        converted_data = rate_data.copy()
                        converted_data["rate"] = converted_rate
                        filtered.append((converted_pair, converted_data))
                    elif base_to_usd_pair in pairs:
                        # Обратный курс найден - конвертируем через него
                        base_to_usd_rate = pairs[base_to_usd_pair]["rate"]
                        usd_to_base_rate = 1.0 / base_to_usd_rate
                        converted_rate = rate_data["rate"] * usd_to_base_rate
                        converted_pair = f"{from_currency}_{target_base}"
                        converted_data = rate_data.copy()
                        converted_data["rate"] = converted_rate
                        filtered.append((converted_pair, converted_data))

        return filtered

    def _display_rates_table(self, pairs: list, args):
        """Отображает курсы в виде таблицы."""
        table = PrettyTable()
        table.field_names = ["Пара валют", "Курс", "Обновлено", "Источник"]
        table.align = "r"
        table.align["Пара валют"] = "l"

        # Сортируем пары
        sorted_pairs = self._sort_rates(pairs, args)

        for pair_key, rate_data in sorted_pairs:
            # Форматируем время
            try:
                dt = datetime.fromisoformat(
                    rate_data["updated_at"].replace("Z", "+00:00")
                )  # noqa: E501
                time_str = dt.strftime("%H:%M:%S")
            except Exception:
                time_str = rate_data["updated_at"]

            table.add_row(
                [
                    pair_key,
                    f"{rate_data['rate']:.8f}",
                    time_str,
                    rate_data.get("source", "Unknown"),
                ]
            )

        print(table)

        # Дополнительная информация для --top
        if args.top:
            print(f"\n📊 Показано топ-{args.top} самых дорогих криптовалют")

    def _sort_rates(self, pairs: list, args) -> list:
        """Сортирует курсы согласно аргументам."""
        if args.top:
            # Для --top сортируем по убыванию курса и берем первые N
            crypto_pairs = [
                (pair, data)
                for pair, data in pairs
                if self._is_crypto(pair.split("_")[0])
            ]
            sorted_crypto = sorted(
                crypto_pairs, key=lambda x: x[1]["rate"], reverse=True
            )
            return sorted_crypto[: args.top]
        else:
            # Обычная сортировка по алфавиту
            return sorted(pairs, key=lambda x: x[0])

    def _is_crypto(self, currency_code: str) -> bool:
        """Проверяет, является ли валюта криптовалютой."""
        crypto_currencies = {"BTC", "ETH", "LTC", "XRP", "ADA", "SOL", "DOT"}
        return currency_code in crypto_currencies

    def _suggest_currency_help(self):
        """Предлагает помощь по валютам при ошибке CurrencyNotFoundError."""
        print(
            "\n💡Для просмотра доступных валют используйте: valutatrade list-currencies"
        )
        print("   Или попробуйте одну из популярных валют: USD, EUR, GBP, BTC, ETH")

    def _handle_register(self, args):
        """Обрабатывает команду register."""
        user = self.user_manager.register_user(args.username, args.password)
        print(f"✅ Пользователь '{user.username}' зарегистрирован (id={user.user_id}).")
        print("🎉 Спасибо за регистрацию! Приветственный бонус - 300 USD!")
        print(
            f"   🔑 Войдите в систему: valutatrade login --username {user.username} --password ****" # noqa: E501
        )

    def _handle_login(self, args):
        """Обрабатывает команду login."""
        user = self.user_manager.authenticate_user(args.username, args.password)
        self.current_user = {"id": user.user_id, "username": user.username}
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

                table.add_row([currency_code, f"{wallet.balance:.4f}", f"{value:.2f}"])
            except (CurrencyNotFoundError, ApiRequestError):
                table.add_row([currency_code, f"{wallet.balance:.4f}", "неизвестно"])

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
                self.current_user["id"], args.currency.upper(), args.amount
            )

            print("✅ Покупка выполнена успешно!")
            print(
                f"   💰 Куплено: {result['amount']:.4f} {result['currency']} ({result['currency_name']})" # noqa: E501
            )
            print(f"   📈 Курс: {result['rate']:.4f} USD/{result['currency']}")
            print(f"   💵 Стоимость: {result['total_cost']:,.2f} USD")
            print("   📊 Изменения баланса:")
            print(
                f"      - {result['currency']}: {result['old_balance']:.4f} → {result['new_balance']:.4f}" # noqa: E501
            )
            print(
                f"      - USD: {result['old_usd_balance']:.2f} → {result['new_usd_balance']:.2f}" # noqa: E501
            )

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
                self.current_user["id"], args.currency.upper(), args.amount
            )

            print("✅ Продажа выполнена успешно!")
            print(
                f"   💰 Продано: {result['amount']:.4f} {result['currency']} ({result['currency_name']})" # noqa: E501
            )
            print(f"   📈 Курс: {result['rate']:.4f} USD/{result['currency']}")
            print(f"   💵 Выручка: {result['total_income']:,.2f} USD")
            print("   📊 Изменения баланса:")
            print(
                f"      - {result['currency']}: {result['old_balance']:.4f} → {result['new_balance']:.4f}" # noqa: E501
            )
            print(
                f"      - USD: {result['old_usd_balance']:.2f} → {result['new_usd_balance']:.2f}" # noqa: E501
            )

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
                reverse_rate = 1.0 / rate_info["rate"]
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
            currency_type = "FIAT" if hasattr(currency, "issuing_country") else "CRYPTO"

            if currency_type == "FIAT":
                extra_info = f"Страна: {currency.issuing_country}"
            else:
                extra_info = f"Алгоритм: {currency.algorithm}"

            table.add_row([code, currency_type, currency.name, extra_info])

        print("📋 Поддерживаемые валюты:")
        print(table)
        print(f"Всего: {len(currencies)} валют")


def main():
    """Точка входа для CLI."""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
