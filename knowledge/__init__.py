"""
Пакет работы со знаниями для AI-ассистента Лиза.
Содержит векторную базу данных, семантический поиск и автодокументирование.
"""

from .vector_db import VectorDatabase
from .semantic_search import SemanticSearch
from .documentation import DocumentationGenerator

__all__ = ['VectorDatabase', 'SemanticSearch', 'DocumentationGenerator']