#!/usr/bin/env python3
"""Точка входа для ValutaTrade Hub."""

from valutatrade_hub.cli.interface import main
from valutatrade_hub.logging_config import setup_logging

if __name__ == "__main__":
    # Настраиваем логирование перед запуском приложения
    setup_logging()
    main()
