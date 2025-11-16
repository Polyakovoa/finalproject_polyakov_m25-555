# ValutaTrade Hub 💰

Консольное приложение для управления валютным кошельком с поддержкой криптовалют.

## 🎯 Идея проекта

ValutaTrade Hub - это полнофункциональное консольное приложение, позволяющее:
- Управлять мультивалютным портфелем
- Совершать торговые операции (покупка/продажа валют)
- Получать актуальные курсы валют из внешних API
- Отслеживать историю операций и изменения баланса

## 📁 Структура проекта
finalproject_polyakov_m25-555/
├── data/
│ ├── users.json (данные пользователей)
│ ├── portfolios.json (портфели и балансы)
│ ├── rates.json (локальный кэш курсов)
│ ├── exchange_rates.json (исторические данные)
│ └── session.json (текущая сессия)
├── valutatrade_hub/
│ ├── core/ (бизнес-логика)
│ │ ├── models.py (User, Wallet, Portfolio)
│ │ ├── currencies.py (Currency, FiatCurrency, CryptoCurrency)
│ │ ├── usecases.py (UserManager, CurrencyService, TradingService)
│ │ ├── exceptions.py (кастомные исключения)
│ │ └── utils.py (утилиты)
│ ├── infra/ (инфраструктура)
│ │ ├── settings.py (Singleton SettingsLoader)
│ │ └── database.py (Singleton DatabaseManager)
│ ├── parser_service/ (сервис парсинга курсов)
│ │ ├── config.py (ParserConfig dataclass)
│ │ ├── api_clients.py (ExchangeRate-API, CoinGecko)
│ │ ├── updater.py (RateUpdater)
│ │ ├── storage.py (RateStorage)
│ │ └── scheduler.py (RateScheduler)
│ ├── cli/ (интерфейс)
│ │ └── interface.py (CLI команды)
│ ├── decorators.py (логирование, кэширование)
│ └── logging_config.py (настройка логов)
├── main.py (точка входа)
├── pyproject.toml (конфигурация Poetry)
├── Makefile (автоматизация)
└── README.md (документация)

## 🚀 Установка и запуск

### Предварительные требования
- Python 3.8+
- Poetry

### Установка
```bash
# Клонирование репозитория
git clone <repository-url>
cd finalproject_polyakov_m25-555

# Установка зависимостей
make install
# или
poetry install
Запуск
bash
# Через Makefile
make project

# Через Poetry
poetry run project
или poetry run valutatrade

# Прямой вызов
poetry run python main.py

💻 Команды CLI
Управление пользователями

# Регистрация (с приветственным бонусом 300 USD!)
valutatrade register --username alice --password 1234

# Вход в систему
valutatrade login --username alice --password 1234

# Выход
valutatrade logout
Портфель и торговля

# Показать портфель (база USD)
valutatrade show-portfolio

# Показать портфель в другой валюте
valutatrade show-portfolio --base EUR

# Купить валюту
valutatrade buy --currency EUR --amount 100

# Продать валюту
valutatrade sell --currency BTC --amount 0.1

# Пополнить баланс
valutatrade add-funds --amount 500
Курсы валют

# Получить курс для пары валют
valutatrade get-rate --from USD --to EUR
valutatrade get-rate --from BTC --to USD

# Показать все курсы из кэша
valutatrade show-rates

# Показать топ криптовалют
valutatrade show-rates --top 3

# Показать курсы для конкретной валюты
valutatrade show-rates --currency EUR

# Показать курсы в другой базовой валюте
valutatrade show-rates --base EUR
Парсер курсов

# Обновить все курсы
valutatrade update-rates

# Обновить только из определенного источника
valutatrade update-rates --source coingecko
valutatrade update-rates --source exchangerate

# Список поддерживаемых валют
valutatrade list-currencies

⚙️ Настройка API

ExchangeRate-API
- Получите API ключ на exchangerate-api.com
- Установите переменную окружения:

export EXCHANGERATE_API_KEY="your_api_key_here"

CoinGecko API
- Получите API ключ на coingecko.com
- Установите переменную окружения (опционально):

export COINGECKO_API_KEY="your_api_key_here"

🔧 Кэш и TTL
- Локальный кэш: data/rates.json - кэшированные курсы валют
- TTL: 1 час (настраивается в settings.py)
- Исторические данные: data/exchange_rates.json - полная история обновлений

При запросе курса система проверяет:
- Локальный кэш (если данные свежие)
- Исторические данные парсера
- Заглушки (fallback)

📊 Поддерживаемые валюты
Фиатные валюты
USD, EUR, GBP, JPY, RUB, CHF, CNY

Криптовалюты
BTC, ETH, LTC, XRP, ADA, SOL, DOT

🎨 Архитектурные особенности
Слоистая архитектура: разделение на core/infra/parser/cli
Синглтоны: SettingsLoader, DatabaseManager
Декораторы: @log_action, @measure_time, @cache_result
Исключения: кастомные исключения для доменной логики
Конфигурация: централизованная через dataclasses

