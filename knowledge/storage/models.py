"""
Модели данных для хранилища знаний AI-ассистента Лиза.
"""

import logging
from peewee import Model, SqliteDatabase, CharField, TextField, DateTimeField, IntegerField, BooleanField
from datetime import datetime
from typing import Optional

# Инициализация базы данных
database = SqliteDatabase('data/knowledge.db')


class BaseModel(Model):
    """Базовая модель для всех моделей данных."""

    class Meta:
        database = database

    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        """Переопределение save для обновления updated_at."""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)


class User(BaseModel):
    """Модель пользователя."""

    username = CharField(unique=True, max_length=50)
    email = CharField(unique=True, max_length=100)
    password_hash = CharField(max_length=255)
    is_active = BooleanField(default=True)
    preferences = TextField(null=True)  # JSON строка с предпочтениями

    class Meta:
        table_name = 'users'


class CommandHistory(BaseModel):
    """Модель истории команд."""

    user = ForeignKeyField(User, backref='commands')
    command_text = TextField()
    response_text = TextField(null=True)
    success = BooleanField(default=True)
    execution_time = IntegerField()  # Время выполнения в миллисекундах
    context = TextField(null=True)  # JSON строка с контекстом выполнения

    class Meta:
        table_name = 'command_history'


class Workflow(BaseModel):
    """Модель workflow."""

    name = CharField(max_length=100)
    description = TextField(null=True)
    definition = TextField()  # JSON строка с определением workflow
    is_active = BooleanField(default=True)
    version = IntegerField(default=1)

    class Meta:
        table_name = 'workflows'


class KnowledgeDocument(BaseModel):
    """Модель документа знаний."""

    title = CharField(max_length=200)
    content = TextField()
    document_type = CharField(max_length=50)  # code, process, concept, etc.
    tags = TextField(null=True)  # JSON строка с тегами
    source = CharField(max_length=200, null=True)  # Источник документа
    vector_id = CharField(max_length=100, null=True)  # ID в векторной базе

    class Meta:
        table_name = 'knowledge_documents'


def create_tables():
    """Создание таблиц в базе данных."""
    try:
        database.connect()
        database.create_tables([User, CommandHistory, Workflow, KnowledgeDocument])
        logging.info("Таблицы базы данных созданы")
    except Exception as e:
        logging.error(f"Ошибка создания таблиц: {e}")
    finally:
        database.close()


def init_database():
    """Инициализация базы данных."""
    # Создание директории данных если не существует
    from pathlib import Path
    Path('data').mkdir(exist_ok=True)

    # Создание таблиц
    create_tables()