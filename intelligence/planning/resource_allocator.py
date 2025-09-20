"""
Аллокатор ресурсов для AI-ассистента Лиза.
"""

import logging
import threading
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum


class AllocationStrategy(Enum):
    """Стратегии распределения ресурсов."""
    BALANCED = "balanced"
    PRIORITY = "priority"
    FIRST_COME = "first_come"


@dataclass
class Resource:
    """Класс ресурса системы."""
    name: str
    total: float  # Общее количество ресурса
    allocated: float = 0.0  # Выделенное количество
    unit: str = "units"  # Единица измерения

    @property
    def available(self) -> float:
        """Доступное количество ресурса."""
        return max(0, self.total - self.allocated)

    @property
    def utilization(self) -> float:
        """Утилизация ресурса в процентах."""
        return (self.allocated / self.total) * 100 if self.total > 0 else 0

    def can_allocate(self, amount: float) -> bool:
        """Проверка возможности выделения указанного количества ресурса."""
        return 0 <= amount <= self.available

    def allocate(self, amount: float) -> bool:
        """Выделение ресурса."""
        if not self.can_allocate(amount):
            return False

        self.allocated += amount
        return True

    def release(self, amount: float) -> bool:
        """Освобождение ресурса."""
        if amount < 0 or amount > self.allocated:
            return False

        self.allocated -= amount
        return True


class ResourceRequest:
    """Запрос на выделение ресурсов."""

    def __init__(self, request_id: str, requirements: Dict[str, float],
                 priority: int = 0, timeout: Optional[float] = None):
        self.id = request_id
        self.requirements = requirements
        self.priority = priority
        self.timeout = timeout
        self.timestamp = time.time()
        self.allocated = False


class ResourceAllocator:
    """Аллокатор ресурсов для управления системными ресурсами."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Реестр ресурсов
        self.resources = {}

        # Очередь запросов на ресурсы
        self.pending_requests = []

        # Блокировка для потокобезопасности
        self.lock = threading.RLock()

        # Отслеживание выделенных ресурсов по ID запроса
        self.allocated_resources = {}

    def register_resource(self, name: str, total: float, unit: str = "units") -> bool:
        """
        Регистрация ресурса в системе.

        Args:
            name: Имя ресурса
            total: Общее количество
            unit: Единица измерения

        Returns:
            True если ресурс успешно зарегистрирован
        """
        with self.lock:
            if name in self.resources:
                self.logger.warning(f"Ресурс {name} уже зарегистрирован")
                return False

            if total <= 0:
                self.logger.error(f"Некорректное количество ресурса {name}: {total}")
                return False

            self.resources[name] = Resource(name, total, 0.0, unit)
            self.logger.info(f"Ресурс зарегистрирован: {name} ({total} {unit})")
            return True

    def request_resources(self, request_id: str, requirements: Dict[str, float],
                          priority: int = 0, timeout: Optional[float] = None) -> bool:
        """
        Запрос выделения ресурсов.

        Args:
            request_id: ID запроса
            requirements: Требования к ресурсам {имя: количество}
            priority: Приоритет запроса
            timeout: Таймаут в секундах (опционально)

        Returns:
            True если ресурсы выделены успешно
        """
        with self.lock:
            # Проверка корректности запроса
            if not self._validate_request(requirements):
                return False

            # Проверка доступности ресурсов
            if self._check_availability(requirements):
                # Выделение ресурсов
                self._allocate_resources(request_id, requirements)
                self.logger.info(f"Ресурсы выделены для запроса {request_id}")
                return True
            else:
                # Добавление в очередь ожидания
                request = ResourceRequest(request_id, requirements, priority, timeout)
                self.pending_requests.append(request)
                self.logger.info(f"Запрос {request_id} добавлен в очередь ожидания")
                return False

    def _validate_request(self, requirements: Dict[str, float]) -> bool:
        """Проверка корректности запроса на ресурсы."""
        for name, amount in requirements.items():
            if name not in self.resources:
                self.logger.error(f"Неизвестный ресурс: {name}")
                return False

            if amount <= 0:
                self.logger.error(f"Некорректное количество ресурса {name}: {amount}")
                return False

        return True

    def _check_availability(self, requirements: Dict[str, float]) -> bool:
        """Проверка доступности ресурсов."""
        for name, amount in requirements.items():
            if not self.resources[name].can_allocate(amount):
                return False
        return True

    def _allocate_resources(self, request_id: str, requirements: Dict[str, float]):
        """Выделение ресурсов."""
        # Сохраняем информацию о выделенных ресурсах
        self.allocated_resources[request_id] = requirements.copy()

        # Выделяем ресурсы
        for name, amount in requirements.items():
            self.resources[name].allocate(amount)

    def release_resources(self, request_id: str) -> bool:
        """
        Освобождение ресурсов.

        Args:
            request_id: ID запроса

        Returns:
            True если ресурсы освобождены успешно
        """
        with self.lock:
            if request_id not in self.allocated_resources:
                self.logger.warning(f"Нет выделенных ресурсов для запроса {request_id}")
                return False

            try:
                resources = self.allocated_resources[request_id]
                for name, amount in resources.items():
                    if name in self.resources:
                        if not self.resources[name].release(amount):
                            self.logger.error(f"Ошибка освобождения ресурса {name} для запроса {request_id}")

                # Удаление из списка выделенных ресурсов
                del self.allocated_resources[request_id]

                self.logger.info(f"Ресурсы освобождены для запроса {request_id}")

                # Проверка очереди ожидания после освобождения ресурсов
                self._process_pending_requests()

                return True

            except Exception as e:
                self.logger.error(f"Ошибка освобождения ресурсов: {e}")
                return False

    def _process_pending_requests(self):
        """Обработка запросов в очереди ожидания."""
        # Удаление просроченных запросов
        current_time = time.time()
        self.pending_requests = [
            req for req in self.pending_requests
            if req.timeout is None or (current_time - req.timestamp) < req.timeout
        ]

        # Сортировка по приоритету и времени
        self.pending_requests.sort(key=lambda x: (-x.priority, x.timestamp))

        # Обработка запросов
        processed_requests = []

        for request in self.pending_requests:
            if self._check_availability(request.requirements):
                self._allocate_resources(request.id, request.requirements)
                processed_requests.append(request)
                request.allocated = True
                self.logger.info(f"Ресурсы выделены для отложенного запроса {request.id}")

        # Удаление обработанных запросов
        self.pending_requests = [req for req in self.pending_requests if not req.allocated]

    def get_resource_utilization(self) -> Dict[str, float]:
        """Получение утилизации всех ресурсов."""
        with self.lock:
            utilization = {}
            for name, resource in self.resources.items():
                utilization[name] = resource.utilization
            return utilization

    def get_available_resources(self) -> Dict[str, float]:
        """Получение доступных ресурсов."""
        with self.lock:
            available = {}
            for name, resource in self.resources.items():
                available[name] = resource.available
            return available

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Получение списка ожидающих запросов."""
        with self.lock:
            return [{
                'id': req.id,
                'requirements': req.requirements,
                'priority': req.priority,
                'timestamp': req.timestamp,
                'timeout': req.timeout
            } for req in self.pending_requests]

    def optimize_allocation(self, strategy: AllocationStrategy = AllocationStrategy.BALANCED) -> Dict[str, Any]:
        """
        Оптимизация распределения ресурсов.

        Args:
            strategy: Стратегия оптимизации

        Returns:
            Результаты оптимизации
        """
        with self.lock:
            if strategy == AllocationStrategy.BALANCED:
                return self._optimize_balanced()
            elif strategy == AllocationStrategy.PRIORITY:
                return self._optimize_priority()
            elif strategy == AllocationStrategy.FIRST_COME:
                return self._optimize_first_come()
            else:
                return {
                    'strategy': strategy.value,
                    'optimized': False,
                    'message': f'Неизвестная стратегия: {strategy}'
                }

    def _optimize_balanced(self) -> Dict[str, Any]:
        """Сбалансированная оптимизация распределения ресурсов."""
        # Базовая реализация - перераспределение для балансировки загрузки
        utilization = self.get_resource_utilization()
        avg_utilization = sum(utilization.values()) / len(utilization) if utilization else 0

        # Здесь можно добавить логику перераспределения ресурсов
        # для выравнивания загрузки

        return {
            'strategy': 'balanced',
            'optimized': True,
            'average_utilization': avg_utilization,
            'message': f'Средняя загрузка ресурсов: {avg_utilization:.2f}%'
        }

    def _optimize_priority(self) -> Dict[str, Any]:
        """Оптимизация по приоритету."""
        # Перераспределение ресурсов в соответствии с приоритетами запросов
        # Сначала обрабатываем запросы с высоким приоритетом

        # Сортируем запросы по приоритету
        self.pending_requests.sort(key=lambda x: -x.priority)

        # Обрабатываем запросы
        processed_count = 0
        for request in self.pending_requests:
            if self._check_availability(request.requirements):
                self._allocate_resources(request.id, request.requirements)
                request.allocated = True
                processed_count += 1

        # Удаляем обработанные запросы
        self.pending_requests = [req for req in self.pending_requests if not req.allocated]

        return {
            'strategy': 'priority',
            'optimized': True,
            'processed_requests': processed_count,
            'message': f'Обработано запросов по приоритету: {processed_count}'
        }

    def _optimize_first_come(self) -> Dict[str, Any]:
        """Оптимизация по принципу 'первым пришел - первым обслужен'."""
        # Обрабатываем запросы в порядке их поступления
        processed_count = 0

        for request in self.pending_requests:
            if self._check_availability(request.requirements):
                self._allocate_resources(request.id, request.requirements)
                request.allocated = True
                processed_count += 1

        # Удаляем обработанные запросы
        self.pending_requests = [req for req in self.pending_requests if not req.allocated]

        return {
            'strategy': 'first_come',
            'optimized': True,
            'processed_requests': processed_count,
            'message': f'Обработано запросов по очереди: {processed_count}'
        }

    def shutdown(self):
        """Корректное завершение работы аллокатора."""
        with self.lock:
            # Освобождение всех выделенных ресурсов
            for request_id in list(self.allocated_resources.keys()):
                self.release_resources(request_id)

            # Очистка очереди запросов
            self.pending_requests.clear()

            self.logger.info("Аллокатор ресурсов завершил работу")