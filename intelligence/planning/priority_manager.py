"""
Менеджер приоритетов для AI-ассистента Лиза.
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum


class PriorityLevel(Enum):
    """Уровни приоритета задач."""
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    NONE = 0


class PriorityManager:
    """Менеджер для определения и управления приоритетами задач."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Веса факторов для расчета приоритета
        self.factor_weights = {
            'deadline': 0.3,
            'importance': 0.25,
            'effort': 0.2,
            'dependencies': 0.15,
            'user_preference': 0.1
        }

        # Правила приоритизации
        self.priority_rules = [
            self._rule_urgent_deadline,
            self._rule_high_importance,
            self._rule_blocked_tasks,
            self._rule_user_preference
        ]

    def calculate_priority(self, task: Dict[str, Any]) -> PriorityLevel:
        """
        Расчет приоритета задачи.

        Args:
            task: Словарь с информацией о задаче

        Returns:
            Уровень приоритета
        """
        try:
            # Базовый расчет на основе факторов
            priority_score = 0

            # Взвешивание факторов
            for factor, weight in self.factor_weights.items():
                factor_value = task.get(factor, 0)
                priority_score += factor_value * weight

            # Применение правил
            for rule in self.priority_rules:
                rule_result = rule(task)
                if rule_result:
                    priority_score += rule_result

            # Нормализация и определение уровня
            return self._score_to_level(priority_score)

        except Exception as e:
            self.logger.error(f"Ошибка расчета приоритета: {e}")
            return PriorityLevel.MEDIUM

    def _score_to_level(self, score: float) -> PriorityLevel:
        """Преобразование score в уровень приоритета."""
        if score >= 0.8:
            return PriorityLevel.CRITICAL
        elif score >= 0.6:
            return PriorityLevel.HIGH
        elif score >= 0.4:
            return PriorityLevel.MEDIUM
        elif score >= 0.2:
            return PriorityLevel.LOW
        else:
            return PriorityLevel.NONE

    def _rule_urgent_deadline(self, task: Dict[str, Any]) -> float:
        """Правило: срочный дедлайн."""
        from datetime import datetime, timedelta

        deadline = task.get('deadline')
        if deadline and isinstance(deadline, str):
            deadline_date = datetime.fromisoformat(deadline)
            days_until_deadline = (deadline_date - datetime.now()).days

            if days_until_deadline <= 1:
                return 0.3  # Высокий бонус за срочность
            elif days_until_deadline <= 3:
                return 0.15

        return 0

    def _rule_high_importance(self, task: Dict[str, Any]) -> float:
        """Правило: высокая важность."""
        importance = task.get('importance', 0)
        if importance >= 0.8:
            return 0.25
        return 0

    def _rule_blocked_tasks(self, task: Dict[str, Any]) -> float:
        """Правило: задачи, которые блокируют другие."""
        blocking_count = task.get('blocking_count', 0)
        if blocking_count > 0:
            return 0.2 * min(blocking_count, 5)  # Максимум 1.0
        return 0

    def _rule_user_preference(self, task: Dict[str, Any]) -> float:
        """Правило: пользовательские предпочтения."""
        user_preference = task.get('user_preference', 0)
        return user_preference * 0.15

    def prioritize_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Приоритизация списка задач.

        Args:
            tasks: Список задач

        Returns:
            Отсортированный список задач по приоритету
        """
        prioritized_tasks = []

        for task in tasks:
            priority = self.calculate_priority(task)
            prioritized_tasks.append({
                **task,
                'priority': priority,
                'priority_score': priority.value
            })

        # Сортировка по приоритету (по убыванию)
        prioritized_tasks.sort(key=lambda x: x['priority_score'], reverse=True)

        return prioritized_tasks

    def adjust_priority_based_on_context(self, task: Dict[str, Any],
                                         context: Dict[str, Any]) -> PriorityLevel:
        """
        Корректировка приоритета на основе контекста.

        Args:
            task: Задача
            context: Контекст выполнения

        Returns:
            Скорректированный уровень приоритета
        """
        base_priority = self.calculate_priority(task)

        # Корректировки на основе контекста
        current_time = context.get('current_time')
        resource_availability = context.get('resource_availability', 1.0)
        user_availability = context.get('user_availability', 1.0)

        # Время суток влияет на приоритет
        if current_time and current_time.hour >= 22 or current_time.hour <= 6:
            # Ночью понижаем приоритет не-critical задач
            if base_priority.value < PriorityLevel.CRITICAL.value:
                return PriorityLevel(max(base_priority.value - 1, 0))

        # Доступность ресурсов влияет на приоритет
        if resource_availability < 0.3:
            # При низкой доступности ресурсов понижаем приоритет
            return PriorityLevel(max(base_priority.value - 1, 0))

        return base_priority