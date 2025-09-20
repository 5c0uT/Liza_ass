"""
Детектор паттернов для AI-ассистента Лиза.
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque


class PatternDetector:
    """Детектор для обнаружения паттернов в данных и поведении."""

    def __init__(self, window_size: int = 10, sensitivity: float = 0.8):
        self.logger = logging.getLogger(__name__)

        self.window_size = window_size
        self.sensitivity = sensitivity

        # Хранилище последовательностей
        self.sequences = defaultdict(lambda: deque(maxlen=window_size))

        # Обнаруженные паттерны
        self.patterns = {}

    def add_sequence(self, sequence_id: str, value: Any):
        """
        Добавление значения в последовательность.

        Args:
            sequence_id: ID последовательности
            value: Значение для добавления
        """
        self.sequences[sequence_id].append(value)

    def detect_pattern(self, sequence_id: str) -> Optional[Dict[str, Any]]:
        """
        Обнаружение паттернов в последовательности.

        Args:
            sequence_id: ID последовательности

        Returns:
            Обнаруженный паттерн или None
        """
        sequence = list(self.sequences[sequence_id])

        if len(sequence) < self.window_size:
            return None  # Недостаточно данных

        # Поиск повторяющихся паттернов
        pattern = self._find_repeating_pattern(sequence)

        if pattern:
            pattern_info = {
                'type': 'repeating',
                'pattern': pattern,
                'length': len(pattern),
                'confidence': self._calculate_confidence(sequence, pattern)
            }

            # Сохранение паттерна
            if sequence_id not in self.patterns:
                self.patterns[sequence_id] = []
            self.patterns[sequence_id].append(pattern_info)

            return pattern_info

        return None

    def _find_repeating_pattern(self, sequence: List[Any]) -> Optional[List[Any]]:
        """Поиск повторяющегося паттерна в последовательности."""
        n = len(sequence)

        # Поиск паттернов разной длины
        for pattern_length in range(1, n // 2 + 1):
            if n % pattern_length != 0:
                continue

            # Проверка повторения паттерна
            pattern = sequence[:pattern_length]
            is_repeating = True

            for i in range(pattern_length, n, pattern_length):
                segment = sequence[i:i + pattern_length]
                if not self._compare_segments(pattern, segment):
                    is_repeating = False
                    break

            if is_repeating:
                return pattern

        return None

    def _compare_segments(self, segment1: List[Any], segment2: List[Any]) -> bool:
        """Сравнение двух сегментов последовательности."""
        if len(segment1) != len(segment2):
            return False

        # Для числовых значений - сравнение с допуском
        if all(isinstance(x, (int, float)) for x in segment1 + segment2):
            tolerance = (1 - self.sensitivity) * 0.1
            for a, b in zip(segment1, segment2):
                if abs(a - b) > tolerance:
                    return False
            return True
        else:
            # Для других типов - точное сравнение
            return segment1 == segment2

    def _calculate_confidence(self, sequence: List[Any], pattern: List[Any]) -> float:
        """Вычисление уверенности в обнаруженном паттерне."""
        pattern_length = len(pattern)
        repetitions = len(sequence) // pattern_length

        # Чем больше повторений, тем выше уверенность
        confidence = min(1.0, repetitions / 3.0)

        # Учет чувствительности
        confidence *= self.sensitivity

        return confidence

    def detect_anomalies(self, sequence_id: str, new_value: Any) -> Optional[Dict[str, Any]]:
        """
        Обнаружение аномалий в последовательности.

        Args:
            sequence_id: ID последовательности
            new_value: Новое значение

        Returns:
            Информация об аномалии или None
        """
        sequence = list(self.sequences[sequence_id])

        if len(sequence) < 2:
            return None  # Недостаточно данных

        # Вычисление статистик последовательности
        if all(isinstance(x, (int, float)) for x in sequence + [new_value]):
            # Для числовых последовательностей
            mean = np.mean(sequence)
            std = np.std(sequence)

            if std == 0:
                return None  # Нет изменений в последовательности

            # Z-score нового значения
            z_score = abs((new_value - mean) / std)

            if z_score > 3.0:  # Порог аномалии
                return {
                    'type': 'numeric_anomaly',
                    'z_score': z_score,
                    'mean': mean,
                    'std': std,
                    'threshold': 3.0
                }

        else:
            # Для категориальных последовательностей
            from collections import Counter
            counter = Counter(sequence)
            most_common = counter.most_common(1)[0][0]

            if new_value != most_common:
                frequency = counter[new_value] / len(sequence) if new_value in counter else 0
                if frequency < 0.1:  # Порог аномалии
                    return {
                        'type': 'categorical_anomaly',
                        'expected': most_common,
                        'actual': new_value,
                        'frequency': frequency
                    }

        return None

    def predict_next(self, sequence_id: str) -> Optional[Any]:
        """
        Предсказание следующего значения в последовательности.

        Args:
            sequence_id: ID последовательности

        Returns:
            Предсказанное значение или None
        """
        sequence = list(self.sequences[sequence_id])

        if not sequence:
            return None

        # Использование обнаруженных паттернов для предсказания
        if sequence_id in self.patterns:
            pattern_info = self.patterns[sequence_id][-1]  # Последний обнаруженный паттерн
            pattern = pattern_info['pattern']
            pattern_length = len(pattern)

            # Предсказание на основе паттерна
            position = len(sequence) % pattern_length
            return pattern[position]

        # Простое предсказание на основе последнего значения
        return sequence[-1]

    def get_sequence_stats(self, sequence_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение статистик последовательности.

        Args:
            sequence_id: ID последовательности

        Returns:
            Статистики последовательности или None
        """
        sequence = list(self.sequences[sequence_id])

        if not sequence:
            return None

        stats = {
            'length': len(sequence),
            'unique_values': len(set(sequence)),
            'is_numeric': all(isinstance(x, (int, float)) for x in sequence)
        }

        if stats['is_numeric']:
            stats.update({
                'mean': float(np.mean(sequence)),
                'std': float(np.std(sequence)),
                'min': float(np.min(sequence)),
                'max': float(np.max(sequence))
            })

        return stats