"""
Модуль мониторинга системы и ресурсов.
"""

import logging
import time
import threading
from typing import Dict, Any, Callable, Optional
from PyQt6.QtCore import QObject, pyqtSignal


class SystemMonitor(QObject):
    """Монитор системы для отслеживания ресурсов и производительности."""

    # Сигналы для уведомлений о событиях
    cpu_alert = pyqtSignal(float)  # Превышение порога CPU
    memory_alert = pyqtSignal(float)  # Превышение порога памяти
    disk_alert = pyqtSignal(float)  # Превышение порога диска

    def __init__(self, check_interval: int = 5):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.check_interval = check_interval
        self.is_monitoring = False
        self.monitor_thread = None

        # Пороги для алертов (в процентах)
        self.cpu_threshold = 90.0
        self.memory_threshold = 85.0
        self.disk_threshold = 90.0

        # Callback функции для пользовательских обработчиков
        self.alert_handlers = []

    def add_alert_handler(self, handler: Callable[[str, float], None]):
        """Добавление обработчика алертов."""
        self.alert_handlers.append(handler)

    def remove_alert_handler(self, handler: Callable[[str, float], None]):
        """Удаление обработчика алертов."""
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)

    def _check_resources(self):
        """Проверка системных ресурсов."""
        import psutil

        try:
            # Получение текущих метрик
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent

            # Проверка порогов и отправка алертов
            if cpu_percent > self.cpu_threshold:
                self.cpu_alert.emit(cpu_percent)
                self._trigger_alert_handlers('cpu', cpu_percent)

            if memory_percent > self.memory_threshold:
                self.memory_alert.emit(memory_percent)
                self._trigger_alert_handlers('memory', memory_percent)

            if disk_percent > self.disk_threshold:
                self.disk_alert.emit(disk_percent)
                self._trigger_alert_handlers('disk', disk_percent)

        except Exception as e:
            self.logger.error(f"Ошибка проверки ресурсов: {e}")

    def _trigger_alert_handlers(self, resource_type: str, value: float):
        """Вызов всех зарегистрированных обработчиков алертов."""
        for handler in self.alert_handlers:
            try:
                handler(resource_type, value)
            except Exception as e:
                self.logger.error(f"Ошибка в обработчике алерта: {e}")

    def _monitor_loop(self):
        """Основной цикл мониторинга."""
        while self.is_monitoring:
            self._check_resources()
            time.sleep(self.check_interval)

    def start_monitoring(self):
        """Запуск мониторинга системы."""
        if self.is_monitoring:
            self.logger.warning("Мониторинг уже запущен")
            return

        self.logger.info("Запуск мониторинга системы")
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Остановка мониторинга системы."""
        self.logger.info("Остановка мониторинга системы")
        self.is_monitoring = False

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)

    def set_thresholds(self, cpu: Optional[float] = None,
                       memory: Optional[float] = None,
                       disk: Optional[float] = None):
        """Установка порогов для алертов."""
        if cpu is not None:
            self.cpu_threshold = cpu
        if memory is not None:
            self.memory_threshold = memory
        if disk is not None:
            self.disk_threshold = disk

        self.logger.info(f"Установлены пороги: CPU={self.cpu_threshold}%, "
                         f"Memory={self.memory_threshold}%, Disk={self.disk_threshold}%")

    def get_current_metrics(self) -> Dict[str, Any]:
        """Получение текущих метрик системы."""
        import psutil

        try:
            return {
                'cpu': psutil.cpu_percent(interval=1),
                'memory': psutil.virtual_memory().percent,
                'disk': psutil.disk_usage('/').percent,
                'process_count': len(psutil.pids()),
                'boot_time': psutil.boot_time(),
                'timestamp': time.time()
            }
        except Exception as e:
            self.logger.error(f"Ошибка получения метрик системы: {e}")
            return {}