"""
Утилиты для настройки логирования.
"""

import logging
import logging.config
from pathlib import Path
from typing import Optional


def setup_logging(config_path: Optional[Path] = None,
                  default_level: int = logging.INFO) -> bool:
    """
    Настройка логирования из конфигурационного файла.

    Args:
        config_path: Путь к файлу конфигурации
        default_level: Уровень логирования по умолчанию

    Returns:
        bool: True если настройка прошла успешно
    """
    try:
        if config_path and config_path.exists():
            logging.config.fileConfig(config_path)
        else:
            # Базовая настройка логирования
            logging.basicConfig(
                level=default_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        # Создание папки для логов если её нет
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        return True

    except Exception as e:
        print(f"Ошибка настройки логирования: {e}")
        logging.basicConfig(level=default_level)
        return False


class LisaLogger:
    """Кастомный логгер для приложения Лиза."""

    def __init__(self, name: str = "lisa"):
        self.logger = logging.getLogger(name)

    def debug(self, message: str, **kwargs):
        """Логирование на уровне DEBUG."""
        self.logger.debug(self._format_message(message, kwargs))

    def info(self, message: str, **kwargs):
        """Логирование на уровне INFO."""
        self.logger.info(self._format_message(message, kwargs))

    def warning(self, message: str, **kwargs):
        """Логирование на уровне WARNING."""
        self.logger.warning(self._format_message(message, kwargs))

    def error(self, message: str, **kwargs):
        """Логирование на уровне ERROR."""
        self.logger.error(self._format_message(message, kwargs))

    def critical(self, message: str, **kwargs):
        """Логирование на уровне CRITICAL."""
        self.logger.critical(self._format_message(message, kwargs))

    def _format_message(self, message: str, context: dict) -> str:
        """Форматирование сообщения с контекстом."""
        if context:
            context_str = " ".join([f"{k}={v}" for k, v in context.items()])
            return f"{message} | {context_str}"
        return message