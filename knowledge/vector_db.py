"""
Модуль векторной базы данных для AI-ассистента Лиза.
Обновлено для совместимости с ChromaDB >= 0.4.0
"""

import logging
import chromadb
from typing import List, Dict, Any, Optional
import uuid


class VectorDatabase:
    """Векторная база данных для хранения и поиска эмбеддингов."""

    def __init__(self, persist_directory: str = "data/vector_db"):
        self.logger = logging.getLogger(__name__)
        self.persist_directory = persist_directory

        try:
            # Новый API ChromaDB
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.logger.info(f"Векторная база данных инициализирована: {persist_directory}")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации векторной БД: {e}")
            raise

        # Коллекции
        self.collections = {}

    def create_collection(self, collection_name: str, metadata: Dict[str, Any] = None):
        """
        Создание коллекции.

        Args:
            collection_name: Имя коллекции
            metadata: Метаданные коллекции
        """
        try:
            if metadata is None:
                metadata = {"hnsw:space": "cosine"}

            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata=metadata
            )

            self.collections[collection_name] = collection
            self.logger.info(f"Коллекция создана/получена: {collection_name}")

        except Exception as e:
            self.logger.error(f"Ошибка создания коллекции: {e}")
            raise

    def get_collection(self, collection_name: str):
        """
        Получение коллекции.

        Args:
            collection_name: Имя коллекции

        Returns:
            Коллекция ChromaDB
        """
        if collection_name in self.collections:
            return self.collections[collection_name]

        try:
            collection = self.client.get_collection(collection_name)
            self.collections[collection_name] = collection
            return collection
        except Exception as e:
            self.logger.error(f"Ошибка получения коллекции: {e}")
            # Попробуем создать коллекцию, если она не существует
            return self.create_collection(collection_name)

    def add_documents(self, collection_name: str, documents: List[str],
                      ids: List[str] = None, metadatas: List[Dict] = None):
        """
        Добавление документов в коллекцию.

        Args:
            collection_name: Имя коллекции
            documents: Список документов
            ids: Список идентификаторов (опционально)
            metadatas: Список метаданных (опционально)
        """
        try:
            collection = self.get_collection(collection_name)

            if ids is None:
                ids = [str(uuid.uuid4()) for _ in documents]

            if metadatas is None:
                metadatas = [{} for _ in documents]

            collection.add(
                documents=documents,
                ids=ids,
                metadatas=metadatas
            )

            self.logger.info(f"Добавлено {len(documents)} документов в коллекцию {collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка добавления документов: {e}")
            return False

    def query(self, collection_name: str, query_text: str,
              n_results: int = 5, where: Dict = None) -> List[Dict[str, Any]]:
        """
        Поиск в коллекции.

        Args:
            collection_name: Имя коллекции
            query_text: Текст запроса
            n_results: Количество результатов
            where: Условия фильтрации

        Returns:
            Список результатов поиска
        """
        try:
            collection = self.get_collection(collection_name)

            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where
            )

            # Преобразование результатов в удобный формат
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'distance': results['distances'][0][i] if results['distances'] else None,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                    })

            return formatted_results

        except Exception as e:
            self.logger.error(f"Ошибка поиска в коллекции: {e}")
            return []

    def get_document(self, collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение документа по ID.

        Args:
            collection_name: Имя коллекции
            document_id: ID документа

        Returns:
            Документ или None если не найден
        """
        try:
            collection = self.get_collection(collection_name)
            results = collection.get(ids=[document_id])

            if results['ids']:
                return {
                    'id': results['ids'][0],
                    'document': results['documents'][0],
                    'metadata': results['metadatas'][0] if results['metadatas'] else {}
                }
            else:
                return None

        except Exception as e:
            self.logger.error(f"Ошибка получения документа: {e}")
            return None

    def update_document(self, collection_name: str, document_id: str,
                        document: str, metadata: Dict = None):
        """
        Обновление документа.

        Args:
            collection_name: Имя коллекции
            document_id: ID документа
            document: Новый текст документа
            metadata: Новые метаданные
        """
        try:
            collection = self.get_collection(collection_name)

            if metadata is None:
                metadata = {}

            collection.update(
                ids=[document_id],
                documents=[document],
                metadatas=[metadata]
            )

            self.logger.info(f"Документ обновлен: {document_id}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка обновления документа: {e}")
            return False

    def delete_document(self, collection_name: str, document_id: str):
        """
        Удаление документа.

        Args:
            collection_name: Имя коллекции
            document_id: ID документа
        """
        try:
            collection = self.get_collection(collection_name)
            collection.delete(ids=[document_id])
            self.logger.info(f"Документ удален: {document_id}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка удаления документа: {e}")
            return False

    def list_collections(self) -> List[str]:
        """Получение списка коллекций."""
        try:
            return [col.name for col in self.client.list_collections()]
        except Exception as e:
            self.logger.error(f"Ошибка получения списка коллекций: {e}")
            return []

    def delete_collection(self, collection_name: str):
        """
        Удаление коллекции.

        Args:
            collection_name: Имя коллекции
        """
        try:
            self.client.delete_collection(collection_name)
            if collection_name in self.collections:
                del self.collections[collection_name]
            self.logger.info(f"Коллекция удалена: {collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка удаления коллекции: {e}")
            return False

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Получение статистики коллекции.

        Args:
            collection_name: Имя коллекции

        Returns:
            Статистика коллекции
        """
        try:
            collection = self.get_collection(collection_name)
            count = collection.count()
            return {
                'name': collection_name,
                'count': count,
                'metadata': collection.metadata
            }
        except Exception as e:
            self.logger.error(f"Ошибка получения статистики коллекции: {e}")
            return {'name': collection_name, 'count': 0, 'metadata': {}}

    def reset_collection(self, collection_name: str):
        """
        Очистка коллекции (удаление всех документов).

        Args:
            collection_name: Имя коллекции
        """
        try:
            # Получаем все ID документов в коллекции
            collection = self.get_collection(collection_name)
            all_documents = collection.get()

            if all_documents['ids']:
                collection.delete(ids=all_documents['ids'])
                self.logger.info(f"Коллекция {collection_name} очищена: удалено {len(all_documents['ids'])} документов")

            return True
        except Exception as e:
            self.logger.error(f"Ошибка очистки коллекции: {e}")
            return False