"""
Рекомендательная система для AI-ассистента Лиза.
"""

import logging
import json
import math
import random
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans


class RecommendationSystem:
    """Рекомендательная система для персонализированных рекомендаций."""

    def __init__(self, data_dir: str = "data/recommendations"):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # База знаний рекомендаций
        self.recommendation_db = []

        # История рекомендаций по пользователям
        self.user_recommendation_history = defaultdict(list)

        # Веса факторов для рекомендаций
        self.factor_weights = {
            'relevance': 0.4,
            'popularity': 0.3,
            'novelty': 0.15,
            'diversity': 0.1,
            'personalization': 0.05
        }

        # Минимальные пороги для рекомендаций
        self.thresholds = {
            'min_relevance': 0.2,
            'min_popularity': 0.1,
            'min_novelty': 0.1
        }

        # Загрузка данных при инициализации
        self.load_data()

    def load_data(self):
        """Загрузка данных рекомендаций из файлов."""
        data_file = self.data_dir / "recommendations.json"
        history_file = self.data_dir / "user_history.json"

        try:
            if data_file.exists():
                with open(data_file, 'r', encoding='utf-8') as f:
                    self.recommendation_db = json.load(f)
                self.logger.info(f"Загружено {len(self.recommendation_db)} рекомендаций")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки данных рекомендаций: {e}")

        try:
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                    self.user_recommendation_history = defaultdict(list, history_data)
                self.logger.info(f"Загружена история для {len(self.user_recommendation_history)} пользователей")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки истории рекомендаций: {e}")

    def save_data(self):
        """Сохранение данных рекомендаций в файлы."""
        data_file = self.data_dir / "recommendations.json"
        history_file = self.data_dir / "user_history.json"

        try:
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(self.recommendation_db, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения данных рекомендаций: {e}")

        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                # Конвертируем defaultdict в обычный dict для сериализации
                regular_dict = dict(self.user_recommendation_history)
                json.dump(regular_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения истории рекомендаций: {e}")

    def add_recommendation(self, item_id: str, item_type: str,
                           features: Dict[str, Any], metadata: Dict[str, Any] = None,
                           content: str = None, tags: List[str] = None):
        """
        Добавление элемента в базу рекомендаций.

        Args:
            item_id: ID элемента
            item_type: Тип элемента (command, workflow, knowledge, etc.)
            features: Features элемента для рекомендаций
            metadata: Дополнительные метаданные
            content: Текстовое содержимое для анализа
            tags: Теги для категоризации
        """
        if metadata is None:
            metadata = {}

        if tags is None:
            tags = []

        recommendation = {
            'item_id': item_id,
            'item_type': item_type,
            'features': features,
            'metadata': metadata,
            'tags': tags,
            'content': content,
            'added_at': datetime.now().isoformat(),
            'usage_count': 0,
            'success_rate': 0.0,
            'last_used': None,
            'embedding': self._generate_embedding(content, tags, features) if content or tags else None
        }

        self.recommendation_db.append(recommendation)
        self.logger.info(f"Рекомендация добавлена: {item_id} ({item_type})")

        # Сохранение данных
        self.save_data()

    def _generate_embedding(self, content: str, tags: List[str], features: Dict[str, Any]) -> List[float]:
        """
        Генерация векторного представления для элемента.

        Args:
            content: Текстовое содержимое
            tags: Список тегов
            features: Features элемента

        Returns:
            Векторное представление
        """
        # Упрощенная реализация генерации эмбеддингов
        # В реальной системе можно использовать предобученные модели

        # Комбинируем все текстовые данные
        text_data = ""
        if content:
            text_data += content + " "
        if tags:
            text_data += " ".join(tags) + " "
        if features:
            for key, value in features.items():
                if isinstance(value, str):
                    text_data += value + " "

        # Простая реализация на основе TF-IDF (упрощенная)
        if text_data:
            # В реальной системе нужно использовать нормальный векторайзер
            # Здесь просто создаем фиктивный вектор для демонстрации
            return [random.random() for _ in range(10)]
        else:
            return [0.0] * 10

    def track_usage(self, user_id: str, item_id: str, success: bool = True,
                   rating: Optional[int] = None, feedback: Optional[str] = None):
        """
        Отслеживание использования рекомендации.

        Args:
            user_id: ID пользователя
            item_id: ID элемента
            success: Успешность использования
            rating: Оценка пользователя (1-5)
            feedback: Текстовый отзыв
        """
        # Обновление общей статистики элемента
        for item in self.recommendation_db:
            if item['item_id'] == item_id:
                item['usage_count'] += 1
                item['last_used'] = datetime.now().isoformat()

                # Обновление success rate
                if item['usage_count'] == 1:
                    item['success_rate'] = 1.0 if success else 0.0
                else:
                    item['success_rate'] = (
                        (item['success_rate'] * (item['usage_count'] - 1) + (1 if success else 0)) /
                        item['usage_count']
                    )
                break

        # Добавление в историю пользователя
        history_entry = {
            'item_id': item_id,
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'rating': rating,
            'feedback': feedback
        }

        self.user_recommendation_history[user_id].append(history_entry)

        # Ограничение истории до последних 100 записей на пользователя
        if len(self.user_recommendation_history[user_id]) > 100:
            self.user_recommendation_history[user_id] = self.user_recommendation_history[user_id][-100:]

        # Сохранение данных
        self.save_data()

    def get_recommendations(self, user_id: str, user_context: Dict[str, Any],
                           max_recommendations: int = 5,
                           diversity_factor: float = 0.3) -> List[Dict[str, Any]]:
        """
        Получение рекомендаций для пользователя.

        Args:
            user_id: ID пользователя
            user_context: Контекст пользователя
            max_recommendations: Максимальное количество рекомендаций
            diversity_factor: Коэффициент разнообразия (0-1)

        Returns:
            Список рекомендаций
        """
        # Получаем историю пользователя
        user_history = self.user_recommendation_history.get(user_id, [])

        # Фильтруем элементы, которые пользователь уже видел/использовал
        seen_items = {entry['item_id'] for entry in user_history}
        candidate_items = [
            item for item in self.recommendation_db
            if item['item_id'] not in seen_items and
            self._passes_minimum_thresholds(item)
        ]

        if not candidate_items:
            # Если нет кандидатов, возвращаем популярные элементы
            candidate_items = sorted(
                [item for item in self.recommendation_db if self._passes_minimum_thresholds(item)],
                key=lambda x: x['usage_count'],
                reverse=True
            )[:max_recommendations]
            return [self._format_recommendation(item, 0.8) for item in candidate_items]

        # Вычисляем score для каждого кандидата
        scored_items = []
        for item in candidate_items:
            score = self._calculate_recommendation_score(item, user_context, user_history, user_id)
            scored_items.append((score, item))

        # Сортировка по score (по убыванию)
        scored_items.sort(key=lambda x: x[0], reverse=True)

        # Применяем diversity для разнообразия рекомендаций
        if diversity_factor > 0:
            scored_items = self._apply_diversity(scored_items, diversity_factor)

        # Выбор top-N рекомендаций
        recommendations = []
        for score, item in scored_items[:max_recommendations]:
            recommendations.append(self._format_recommendation(item, score))

            # Записываем в историю, что рекомендовали этот элемент
            self.user_recommendation_history[user_id].append({
                'item_id': item['item_id'],
                'timestamp': datetime.now().isoformat(),
                'recommended': True,
                'viewed': False
            })

        # Сохранение данных
        self.save_data()

        return recommendations

    def _passes_minimum_thresholds(self, item: Dict[str, Any]) -> bool:
        """Проверка, проходит ли элемент минимальные пороги для рекомендации."""
        # Проверка popularity
        if item['usage_count'] > 0 and item['success_rate'] < self.thresholds['min_popularity']:
            return False

        # Проверка novelty (если элемент слишком старый)
        if item['last_used']:
            last_used = datetime.fromisoformat(item['last_used'])
            days_since_used = (datetime.now() - last_used).days
            novelty = min(days_since_used / 30.0, 1.0)
            if novelty < self.thresholds['min_novelty']:
                return False

        return True

    def _calculate_recommendation_score(self, item: Dict[str, Any],
                                       user_context: Dict[str, Any],
                                       user_history: List[Dict[str, Any]],
                                       user_id: str) -> float:
        """
        Вычисление score рекомендации.

        Args:
            item: Элемент рекомендации
            user_context: Контекст пользователя
            user_history: История пользователя
            user_id: ID пользователя

        Returns:
            Score рекомендации
        """
        total_score = 0

        # Relevance - соответствие контексту пользователя
        relevance_score = self._calculate_relevance(item, user_context)
        if relevance_score < self.thresholds['min_relevance']:
            return 0  # Пропускаем элементы с низкой релевантностью

        total_score += relevance_score * self.factor_weights['relevance']

        # Popularity - популярность элемента
        popularity_score = self._calculate_popularity(item)
        total_score += popularity_score * self.factor_weights['popularity']

        # Novelty - новизна для пользователя
        novelty_score = self._calculate_novelty(item, user_history)
        total_score += novelty_score * self.factor_weights['novelty']

        # Diversity - разнообразие рекомендаций
        diversity_score = self._calculate_diversity(item, user_id)
        total_score += diversity_score * self.factor_weights['diversity']

        # Personalization - персонализация на основе профиля
        personalization_score = self._calculate_personalization(item, user_context)
        total_score += personalization_score * self.factor_weights['personalization']

        return total_score

    def _calculate_relevance(self, item: Dict[str, Any],
                            user_context: Dict[str, Any]) -> float:
        """Вычисление relevance score."""
        # Анализ контекста пользователя и характеристик элемента
        context_tasks = user_context.get('current_tasks', [])
        context_skills = user_context.get('skill_level', {})
        context_interests = user_context.get('interests', [])

        relevance = 0.0

        # Проверка соответствия текущим задачам
        if context_tasks and item['metadata'].get('related_tasks'):
            task_overlap = set(context_tasks) & set(item['metadata'].get('related_tasks', []))
            if task_overlap:
                relevance += 0.3 * len(task_overlap)

        # Проверка соответствия уровню навыков
        if context_skills and item['metadata'].get('required_skills'):
            for skill, level in item['metadata'].get('required_skills', {}).items():
                user_skill = context_skills.get(skill, 0)
                if user_skill >= level:
                    relevance += 0.2
                else:
                    relevance += 0.1 * (user_skill / max(level, 0.1))

        # Проверка соответствия интересам
        if context_interests and item['tags']:
            interest_overlap = set(context_interests) & set(item['tags'])
            if interest_overlap:
                relevance += 0.2 * len(interest_overlap)

        # Проверка типа элемента
        preferred_types = user_context.get('preferred_types', [])
        if preferred_types and item['item_type'] in preferred_types:
            relevance += 0.1

        return min(relevance, 1.0)

    def _calculate_popularity(self, item: Dict[str, Any]) -> float:
        """Вычисление popularity score."""
        usage_count = item['usage_count']
        success_rate = item['success_rate']

        # Нормализация usage_count (логарифмическая шкала)
        pop_score = math.log1p(usage_count) / 10.0  # 0-1 scale

        # Учет success_rate
        pop_score *= success_rate

        return min(pop_score, 1.0)

    def _calculate_novelty(self, item: Dict[str, Any],
                          user_history: List[Dict[str, Any]]) -> float:
        """Вычисление novelty score."""
        # Новизна основана на том, как давно элемент использовался
        last_used = item.get('last_used')

        if last_used is None:
            return 1.0  # Никогда не использовался - максимальная новизна

        if isinstance(last_used, str):
            last_used = datetime.fromisoformat(last_used)

        days_since_used = (datetime.now() - last_used).days

        # Чем больше дней прошло, тем выше новизна
        novelty = min(days_since_used / 30.0, 1.0)  # 0-1 scale за 30 дней

        return novelty

    def _calculate_diversity(self, item: Dict[str, Any], user_id: str) -> float:
        """Вычисление diversity score."""
        # Анализ истории рекомендаций пользователя
        user_history = self.user_recommendation_history.get(user_id, [])

        if not user_history:
            return 0.5  # Среднее значение для новых пользователей

        # Анализ типов ранее рекомендованных элементов
        recent_recommendations = [
            rec for rec in user_history[-10:]  # Последние 10 рекомендаций
            if rec.get('recommended', False)
        ]

        if not recent_recommendations:
            return 0.5

        # Подсчет типов в истории
        type_counts = Counter()
        for rec in recent_recommendations:
            for db_item in self.recommendation_db:
                if db_item['item_id'] == rec['item_id']:
                    type_counts[db_item['item_type']] += 1
                    break

        # Если этот тип еще не рекомендовался или рекомендовался мало раз - выше diversity
        current_type_count = type_counts.get(item['item_type'], 0)
        diversity = 1.0 - (current_type_count / len(recent_recommendations))

        return diversity

    def _calculate_personalization(self, item: Dict[str, Any],
                                  user_context: Dict[str, Any]) -> float:
        """Вычисление personalization score."""
        # Персонализация на основе похожих пользователей
        # В реальной системе здесь была бы коллаборативная фильтрация

        # Временная реализация - случайное значение
        return random.uniform(0.2, 0.5)

    def _apply_diversity(self, scored_items: List[tuple], diversity_factor: float) -> List[tuple]:
        """Применение diversity к списку рекомендаций."""
        if len(scored_items) <= 1:
            return scored_items

        # Группируем элементы по типам
        type_groups = defaultdict(list)
        for score, item in scored_items:
            type_groups[item['item_type']].append((score, item))

        # Сортируем элементы внутри каждой группы по score
        for group in type_groups.values():
            group.sort(key=lambda x: x[0], reverse=True)

        # Применяем diversity алгоритм (Maximal Marginal Relevance)
        diverse_results = []
        selected_types = set()

        # Первый элемент - самый релевантный
        if scored_items:
            diverse_results.append(scored_items[0])
            selected_types.add(scored_items[0][1]['item_type'])

        # Добавляем элементы из разных групп
        for i in range(1, len(scored_items)):
            best_candidate = None
            best_score = -1

            for score, item in scored_items:
                if (score, item) in diverse_results:
                    continue

                # Вычисляем diversity score
                type_diversity = 0.0
                if item['item_type'] not in selected_types:
                    type_diversity = 1.0

                # Комбинируем relevance и diversity
                combined_score = (1 - diversity_factor) * score + diversity_factor * type_diversity

                if combined_score > best_score:
                    best_score = combined_score
                    best_candidate = (score, item)

            if best_candidate:
                diverse_results.append(best_candidate)
                selected_types.add(best_candidate[1]['item_type'])

        return diverse_results

    def _format_recommendation(self, item: Dict[str, Any], score: float) -> Dict[str, Any]:
        """Форматирование рекомендации для возврата."""
        return {
            'item_id': item['item_id'],
            'item_type': item['item_type'],
            'score': round(score, 3),
            'features': item['features'],
            'metadata': item['metadata'],
            'tags': item['tags'],
            'confidence': self._calculate_confidence(score, item)
        }

    def _calculate_confidence(self, score: float, item: Dict[str, Any]) -> float:
        """Вычисление уверенности в рекомендации."""
        # Уверенность основана на качестве данных и количестве использований
        usage_confidence = min(item['usage_count'] / 10.0, 1.0)  # 0-1 based on usage count
        success_confidence = item['success_rate']  # 0-1 based on success rate

        # Комбинируем с score
        confidence = score * 0.5 + usage_confidence * 0.3 + success_confidence * 0.2

        return round(confidence, 3)

    def generate_personalized_recommendations(self, user_id: str, user_profile: Dict[str, Any],
                                             current_task: str = None) -> List[Dict[str, Any]]:
        """
        Генерация персонализированных рекомендаций.

        Args:
            user_id: ID пользователя
            user_profile: Профиль пользователя
            current_task: Текущая задача (опционально)

        Returns:
            Список персонализированных рекомендаций
        """
        # Анализ профиля пользователя для рекомендаций
        user_skill = user_profile.get('skill_level', {})
        user_behavior = user_profile.get('behavior_patterns', {})
        user_preferences = user_profile.get('preferences', {})

        # Формирование контекста пользователя
        user_context = {
            'skill_level': user_skill,
            'frequent_commands': [cmd['command'] for cmd in user_behavior.get('frequent_commands', [])],
            'interests': user_behavior.get('preferred_apps', []),
            'preferred_types': user_preferences.get('preferred_content_types', []),
            'current_tasks': [current_task] if current_task else []
        }

        return self.get_recommendations(user_id, user_context)

    def optimize_recommendations(self, feedback_data: List[Dict[str, Any]]):
        """
        Оптимизация рекомендаций на основе feedback.

        Args:
            feedback_data: Данные обратной связи
        """
        self.logger.info(f"Получен feedback для оптимизации: {len(feedback_data)} записей")

        for feedback in feedback_data:
            user_id = feedback.get('user_id')
            item_id = feedback.get('item_id')
            success = feedback.get('success', True)
            rating = feedback.get('rating')
            comments = feedback.get('comments')

            if user_id and item_id:
                self.track_usage(user_id, item_id, success, rating, comments)

        # Адаптация весов на основе feedback
        self._adapt_weights_based_on_feedback(feedback_data)

    def _adapt_weights_based_on_feedback(self, feedback_data: List[Dict[str, Any]]):
        """Адаптация весов факторов на основе обратной связи."""
        if not feedback_data:
            return

        # Анализ успешных рекомендаций
        successful_feedback = [fb for fb in feedback_data if fb.get('success', False)]

        if not successful_feedback:
            return

        # В реальной системе здесь был бы более сложный анализ
        # и адаптация весов на основе машинного обучения

        # Упрощенная реализация: увеличиваем вес факторов, которые чаще
        # встречаются в успешных рекомендациях
        self.logger.info("Адаптация весов факторов на основе обратной связи")

    def get_user_recommendation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получение истории рекомендаций пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей

        Returns:
            История рекомендаций
        """
        history = self.user_recommendation_history.get(user_id, [])

        # Обогащаем историю данными элементов
        enriched_history = []
        for entry in history[-limit:]:
            item_data = next((item for item in self.recommendation_db
                             if item['item_id'] == entry['item_id']), None)

            if item_data:
                enriched_entry = entry.copy()
                enriched_entry['item_data'] = {
                    'item_type': item_data['item_type'],
                    'features': item_data['features'],
                    'tags': item_data['tags']
                }
                enriched_history.append(enriched_entry)

        return enriched_history

    def get_popular_recommendations(self, item_type: Optional[str] = None,
                                   limit: int = 5) -> List[Dict[str, Any]]:
        """
        Получение популярных рекомендаций.

        Args:
            item_type: Фильтр по типу (опционально)
            limit: Максимальное количество

        Returns:
            Список популярных рекомендаций
        """
        # Фильтрация по типу
        items = self.recommendation_db
        if item_type:
            items = [item for item in items if item['item_type'] == item_type]

        # Сортировка по популярности
        popular_items = sorted(
            items,
            key=lambda x: (x['usage_count'], x['success_rate']),
            reverse=True
        )[:limit]

        return [self._format_recommendation(item, 0.8) for item in popular_items]

    def find_similar_items(self, item_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск похожих элементов.

        Args:
            item_id: ID элемента
            limit: Максимальное количество

        Returns:
            Список похожих элементов
        """
        # Поиск целевого элемента
        target_item = next((item for item in self.recommendation_db
                           if item['item_id'] == item_id), None)

        if not target_item or not target_item.get('embedding'):
            return []

        # Вычисление схожести с другими элементами
        similarities = []
        for item in self.recommendation_db:
            if item['item_id'] == item_id or not item.get('embedding'):
                continue

            # Вычисление косинусной схожести
            similarity = self._cosine_similarity(
                target_item['embedding'],
                item['embedding']
            )

            similarities.append((similarity, item))

        # Сортировка по схожести
        similarities.sort(key=lambda x: x[0], reverse=True)

        return [self._format_recommendation(item, sim) for sim, item in similarities[:limit]]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Вычисление косинусной схожести между векторами."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def update_factor_weights(self, new_weights: Dict[str, float]):
        """
        Обновление весов факторов рекомендаций.

        Args:
            new_weights: Новые веса факторов
        """
        # Проверка, что сумма весов равна 1
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            self.logger.error("Сумма весов факторов должна быть равна 1.0")
            return

        self.factor_weights = new_weights
        self.logger.info(f"Обновлены веса факторов: {new_weights}")

    def shutdown(self):
        """Корректное завершение работы системы рекомендаций."""
        self.save_data()
        self.logger.info("Рекомендательная система завершила работу")