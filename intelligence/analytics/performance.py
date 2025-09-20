"""
Анализ производительности для AI-ассистента Лиза.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class PerformanceAnalyzer:
    """Анализатор производительности системы и компонентов."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Метрики производительности
        self.metrics = {
            'response_times': {},
            'memory_usage': {},
            'cpu_usage': {},
            'error_rates': {}
        }

        # Временные метки для измерения
        self.timers = {}

    def start_timer(self, operation_id: str):
        """
        Запуск таймера для операции.

        Args:
            operation_id: ID операции
        """
        self.timers[operation_id] = time.time()

    def stop_timer(self, operation_id: str) -> Optional[float]:
        """
        Остановка таймера и запись результата.

        Args:
            operation_id: ID операции

        Returns:
            Время выполнения в секундах или None
        """
        if operation_id not in self.timers:
            return None

        start_time = self.timers[operation_id]
        duration = time.time() - start_time

        # Запись метрики
        self.record_response_time(operation_id, duration)

        # Удаление таймера
        del self.timers[operation_id]

        return duration

    def record_response_time(self, operation_id: str, response_time: float):
        """
        Запись времени отклика.

        Args:
            operation_id: ID операции
            response_time: Время отклика в секундах
        """
        if operation_id not in self.metrics['response_times']:
            self.metrics['response_times'][operation_id] = []

        self.metrics['response_times'][operation_id].append({
            'timestamp': datetime.now(),
            'response_time': response_time
        })

    def record_memory_usage(self, component: str, memory_mb: float):
        """
        Запись использования памяти.

        Args:
            component: Компонент системы
            memory_mb: Использование памяти в МБ
        """
        if component not in self.metrics['memory_usage']:
            self.metrics['memory_usage'][component] = []

        self.metrics['memory_usage'][component].append({
            'timestamp': datetime.now(),
            'memory_mb': memory_mb
        })

    def record_cpu_usage(self, component: str, cpu_percent: float):
        """
        Запись использования CPU.

        Args:
            component: Компонент системы
            cpu_percent: Использование CPU в процентах
        """
        if component not in self.metrics['cpu_usage']:
            self.metrics['cpu_usage'][component] = []

        self.metrics['cpu_usage'][component].append({
            'timestamp': datetime.now(),
            'cpu_percent': cpu_percent
        })

    def record_error(self, component: str, error_type: str):
        """
        Запись ошибки.

        Args:
            component: Компонент системы
            error_type: Тип ошибки
        """
        if component not in self.metrics['error_rates']:
            self.metrics['error_rates'][component] = {}

        if error_type not in self.metrics['error_rates'][component]:
            self.metrics['error_rates'][component][error_type] = []

        self.metrics['error_rates'][component][error_type].append(datetime.now())

    def get_performance_report(self, component: str = None,
                               time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """
        Получение отчета о производительности.

        Args:
            component: Компонент системы (опционально)
            time_window: Временное окно для анализа

        Returns:
            Отчет о производительности
        """
        report = {
            'response_times': {},
            'memory_usage': {},
            'cpu_usage': {},
            'error_rates': {}
        }

        cutoff_time = datetime.now() - time_window

        # Анализ response times
        for op_id, measurements in self.metrics['response_times'].items():
            if component and not op_id.startswith(component):
                continue

            recent_measurements = [
                m for m in measurements if m['timestamp'] >= cutoff_time
            ]

            if recent_measurements:
                times = [m['response_time'] for m in recent_measurements]
                report['response_times'][op_id] = {
                    'count': len(times),
                    'avg': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                    'p95': self._calculate_percentile(times, 95)
                }

        # Анализ memory usage
        for comp, measurements in self.metrics['memory_usage'].items():
            if component and comp != component:
                continue

            recent_measurements = [
                m for m in measurements if m['timestamp'] >= cutoff_time
            ]

            if recent_measurements:
                usage = [m['memory_mb'] for m in recent_measurements]
                report['memory_usage'][comp] = {
                    'avg': sum(usage) / len(usage),
                    'min': min(usage),
                    'max': max(usage),
                    'trend': self._calculate_trend(usage)
                }

        # Анализ CPU usage
        for comp, measurements in self.metrics['cpu_usage'].items():
            if component and comp != component:
                continue

            recent_measurements = [
                m for m in measurements if m['timestamp'] >= cutoff_time
            ]

            if recent_measurements:
                usage = [m['cpu_percent'] for m in recent_measurements]
                report['cpu_usage'][comp] = {
                    'avg': sum(usage) / len(usage),
                    'min': min(usage),
                    'max': max(usage),
                    'trend': self._calculate_trend(usage)
                }

        # Анализ error rates
        for comp, errors_by_type in self.metrics['error_rates'].items():
            if component and comp != component:
                continue

            report['error_rates'][comp] = {}
            for error_type, timestamps in errors_by_type.items():
                recent_errors = [
                    t for t in timestamps if t >= cutoff_time
                ]
                report['error_rates'][comp][error_type] = len(recent_errors)

        return report

    def _calculate_percentile(self, data: List[float], percentile: float) -> float:
        """Вычисление перцентиля."""
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = (len(sorted_data) - 1) * percentile / 100
        lower_index = int(index)
        upper_index = lower_index + 1

        if upper_index >= len(sorted_data):
            return sorted_data[lower_index]

        # Интерполяция
        return sorted_data[lower_index] + (sorted_data[upper_index] - sorted_data[lower_index]) * (index - lower_index)

    def _calculate_trend(self, data: List[float]) -> float:
        """Вычисление тренда данных."""
        if len(data) < 2:
            return 0.0

        # Простой линейный тренд
        from scipy import stats
        x = list(range(len(data)))
        slope, _, _, _, _ = stats.linregress(x, data)
        return slope

    def identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        Идентификация узких мест производительности.

        Returns:
            Список узких мест
        """
        bottlenecks = []

        # Анализ response times
        report = self.get_performance_report(time_window=timedelta(hours=24))

        for operation, stats in report['response_times'].items():
            if stats['p95'] > 1.0:  # Порог 1 секунда
                bottlenecks.append({
                    'type': 'response_time',
                    'component': operation,
                    'metric': 'p95_response_time',
                    'value': stats['p95'],
                    'threshold': 1.0,
                    'severity': 'high' if stats['p95'] > 2.0 else 'medium'
                })

        # Анализ memory usage
        for component, stats in report['memory_usage'].items():
            if stats['avg'] > 512:  # Порог 512 МБ
                bottlenecks.append({
                    'type': 'memory_usage',
                    'component': component,
                    'metric': 'average_memory',
                    'value': stats['avg'],
                    'threshold': 512,
                    'severity': 'high' if stats['avg'] > 1024 else 'medium'
                })

        # Анализ error rates
        for component, errors in report['error_rates'].items():
            total_errors = sum(errors.values())
            if total_errors > 10:  # Порог 10 ошибок в день
                bottlenecks.append({
                    'type': 'error_rate',
                    'component': component,
                    'metric': 'total_errors',
                    'value': total_errors,
                    'threshold': 10,
                    'severity': 'high' if total_errors > 50 else 'medium'
                })

        return bottlenecks

    def generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """
        Генерация рекомендаций по оптимизации.

        Returns:
            Список рекомендаций
        """
        recommendations = []
        bottlenecks = self.identify_bottlenecks()

        for bottleneck in bottlenecks:
            if bottleneck['type'] == 'response_time':
                recommendations.append({
                    'type': 'optimization',
                    'component': bottleneck['component'],
                    'issue': 'Высокое время отклика',
                    'suggestion': 'Рассмотрите кэширование, оптимизацию алгоритмов или асинхронную обработку',
                    'priority': bottleneck['severity']
                })

            elif bottleneck['type'] == 'memory_usage':
                recommendations.append({
                    'type': 'optimization',
                    'component': bottleneck['component'],
                    'issue': 'Высокое использование памяти',
                    'suggestion': 'Оптимизируйте использование памяти, добавьте очистку или увеличьте ресурсы',
                    'priority': bottleneck['severity']
                })

            elif bottleneck['type'] == 'error_rate':
                recommendations.append({
                    'type': 'stability',
                    'component': bottleneck['component'],
                    'issue': 'Высокий уровень ошибок',
                    'suggestion': 'Исследуйте и исправьте источники ошибок, добавьте обработку исключений',
                    'priority': bottleneck['severity']
                })

        return recommendations