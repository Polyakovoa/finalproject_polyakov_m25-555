"""Планировщик для периодического обновления курсов."""

import logging
import threading
import time
from typing import Optional

from .config import ParserConfig
from .updater import RateUpdater

logger = logging.getLogger("valutatrade.parser.scheduler")


class RateScheduler:
    """Планировщик для автоматического обновления курсов."""

    def __init__(self):
        self.updater = RateUpdater()
        self.scheduler_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.update_interval = ParserConfig.UPDATE_INTERVAL

    def start(self) -> bool:
        """
        Запускает фоновый планировщик.

        Returns:
            True если планировщик успешно запущен
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return False

        self.is_running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True
        )  # noqa: E501
        self.scheduler_thread.start()

        logger.info(f"Scheduler started with {self.update_interval} second interval")
        return True

    def stop(self) -> bool:
        """
        Останавливает планировщик.

        Returns:
            True если планировщик успешно остановлен
        """
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return False

        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)

        logger.info("Scheduler stopped")
        return True

    def _scheduler_loop(self) -> None:
        """Основной цикл планировщика."""
        logger.info("Scheduler loop started")

        while self.is_running:
            try:
                # Выполняем обновление
                stats = self.updater.update_rates()

                # Обновляем локальный кэш
                if stats["total_updated"] > 0:
                    self.updater.update_local_cache()

                logger.info(f"Scheduled update completed: {stats}")

            except Exception as e:
                logger.error(f"Scheduled update failed: {e}")

            # Ждем до следующего обновления
            for _ in range(self.update_interval):
                if not self.is_running:
                    break
                time.sleep(1)

        logger.info("Scheduler loop stopped")

    def force_update(self) -> dict:
        """
        Принудительно выполняет обновление курсов.

        Returns:
            Статистика обновления
        """
        logger.info("Manual rate update triggered")

        try:
            stats = self.updater.update_rates()

            # Обновляем локальный кэш если были обновления
            if stats["total_updated"] > 0:
                self.updater.update_local_cache()

            logger.info(f"Manual update completed: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Manual update failed: {e}")
            return {"error": str(e), "total_updated": 0}

    def get_status(self) -> dict:
        """
        Возвращает статус планировщика.

        Returns:
            Словарь со статусом
        """
        return {
            "is_running": self.is_running,
            "update_interval": self.update_interval,
            "last_update": self.updater.get_update_status(),
        }
