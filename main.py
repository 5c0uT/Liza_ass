#!/usr/bin/env python3
"""
Главная точка входа в приложение AI-ассистента "Лиза".
"""

import sys
import os
import logging
import logging.config
from pathlib import Path

# Добавляем корневую директорию в путь для импортов
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from utilities.loggers import setup_logging
from utilities.helpers import load_config

def setup_environment():
    """Настройка окружения приложения."""
    # Создание необходимых директорий
    directories = [
        'logs',
        'data',
        'backups',
        'config',
        'models',
        'workflows',
        'data/profiles',
        'data/vector_db',
        'data/recommendations',
        'data/anomalies',
        'data/productivity',
        'data/telegram'
    ]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

    # Настройка переменных окружения
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
    os.environ['QT_SCALE_FACTOR'] = '1'
    os.environ['QT_SCREEN_SCALE_FACTORS'] = '1'

def main():
    """Основная функция запуска приложения."""
    try:
        # Настройка окружения
        setup_environment()

        # Настройка логирования
        log_config_path = ROOT_DIR / 'config' / 'logging.conf'
        setup_logging(log_config_path)

        logger = logging.getLogger(__name__)
        logger.info("Запуск AI-ассистента Лиза v1.0.0")
        logger.info(f"Рабочая директория: {ROOT_DIR}")

        # Загрузка конфигурации
        config_path = ROOT_DIR / 'config' / 'settings.toml'
        config = load_config(config_path)

        if not config:
            logger.error("Не удалось загрузить конфигурацию. Используются настройки по умолчанию.")
            config = {}

        # Создание и настройка приложения Qt
        app = QApplication(sys.argv)
        app.setApplicationName("Lisa Assistant")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Lisa Technologies")

        # Установка иконки приложения
        icon_path = ROOT_DIR / 'assets' / 'icons' / 'app_icon.png'
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

        # Создание и запуск основного приложения
        from core.app import LisaApp
        lisa_app = LisaApp()

        # Запуск приложения
        return lisa_app.run()

    except Exception as e:
        print(f"Критическая ошибка при запуске приложения: {e}")
        if 'logger' in locals():
            logger.critical("Критическая ошибка при запуске приложения", exc_info=True)
        else:
            # Создаем базовый логгер для записи ошибки
            logging.basicConfig(level=logging.CRITICAL)
            logging.critical("Критическая ошибка при запуске приложения", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())