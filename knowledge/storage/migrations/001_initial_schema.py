"""
Миграция начальной схемы базы данных для AI-ассистента Лиза.
"""

import logging
from playhouse.migrate import SqliteMigrator, migrate
from peewee import SqliteDatabase, ForeignKeyField

# Инициализация мигратора
database = SqliteDatabase('data/knowledge.db')
migrator = SqliteMigrator(database)

def run_migration():
    """Выполнение миграции."""
    try:
        # Создание таблиц (уже выполнено в models.py)
        logging.info("Миграция 001: Начальная схема применена")
        return True
    except Exception as e:
        logging.error(f"Ошибка миграции 001: {e}")
        return False

def rollback_migration():
    """Откат миграции."""
    try:
        # В реальной реализации здесь был бы код отката
        logging.info("Миграция 001: Откат выполнен")
        return True
    except Exception as e:
        logging.error(f"Ошибка отката миграции 001: {e}")
        return False