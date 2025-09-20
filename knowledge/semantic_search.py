"""
Модуль семантического поиска для AI-ассистента Лиза.
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class SemanticSearch:
    """Семантический поиск по базе знаний."""

    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.logger = logging.getLogger(__name__)

        # Загрузка модели для эмбеддингов
        self.model = SentenceTransformer(model_name)
        self.embeddings = {}
        self.documents = []

    def add_documents(self, documents: List[str], ids: List[str] = None):
        """
        Добавление документов для поиска.

        Args:
            documents: Список документов
            ids: Список идентификаторов документов (опционально)
        """
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]

        if len(documents) != len(ids):
            raise ValueError("Количество документов и идентификаторов должно совпадать")

        # Создание эмбеддингов для документов
        doc_embeddings = self.model.encode(documents)

        for doc_id, doc, embedding in zip(ids, documents, doc_embeddings):
            self.embeddings[doc_id] = embedding
            self.documents.append({
                'id': doc_id,
                'text': doc,
                'embedding': embedding
            })

        self.logger.info(f"Добавлено {len(documents)} документов для поиска")

    def search(self, query: str, top_k: int = 5, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Семантический поиск по документам.

        Args:
            query: Поисковый запрос
            top_k: Количество результатов
            threshold: Порог похожести

        Returns:
            Список результатов поиска
        """
        if not self.documents:
            self.logger.warning("Нет документов для поиска")
            return []

        # Создание эмбеддинга для запроса
        query_embedding = self.model.encode([query])[0]

        # Вычисление похожести
        similarities = []
        for doc in self.documents:
            similarity = cosine_similarity(
                [query_embedding],
                [doc['embedding']]
            )[0][0]
            similarities.append((doc, similarity))

        # Сортировка по убыванию похожести
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Фильтрация по порогу и выбор top_k результатов
        results = []
        for doc, similarity in similarities[:top_k]:
            if similarity >= threshold:
                results.append({
                    'id': doc['id'],
                    'text': doc['text'],
                    'similarity': similarity
                })

        return results

    def find_similar(self, document_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск похожих документов.

        Args:
            document_id: ID документа
            top_k: Количество результатов

        Returns:
            Список похожих документов
        """
        if document_id not in self.embeddings:
            self.logger.error(f"Документ с ID {document_id} не найден")
            return []

        # Получение эмбеддинга целевого документа
        target_embedding = self.embeddings[document_id]

        # Вычисление похожести со всеми документами
        similarities = []
        for doc_id, embedding in self.embeddings.items():
            if doc_id != document_id:
                similarity = cosine_similarity(
                    [target_embedding],
                    [embedding]
                )[0][0]
                similarities.append((doc_id, similarity))

        # Сортировка по убыванию похожести
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Выбор top_k результатов
        results = []
        for doc_id, similarity in similarities[:top_k]:
            # Поиск текста документа
            doc_text = next((doc['text'] for doc in self.documents if doc['id'] == doc_id), "")
            results.append({
                'id': doc_id,
                'text': doc_text,
                'similarity': similarity
            })

        return results

    def clear_documents(self):
        """Очистка всех документов."""
        self.embeddings = {}
        self.documents = []
        self.logger.info("Все документы очищены")

    def save_index(self, file_path: str):
        """
        Сохранение индекса поиска.

        Args:
            file_path: Путь для сохранения
        """
        import pickle

        try:
            data = {
                'embeddings': self.embeddings,
                'documents': self.documents
            }

            with open(file_path, 'wb') as f:
                pickle.dump(data, f)

            self.logger.info(f"Индекс поиска сохранен: {file_path}")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения индекса: {e}")

    def load_index(self, file_path: str):
        """
        Загрузка индекса поиска.

        Args:
            file_path: Путь к файлу индекса
        """
        import pickle

        try:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)

            self.embeddings = data['embeddings']
            self.documents = data['documents']

            self.logger.info(f"Индекс поиска загружен: {file_path}")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки индекса: {e}")