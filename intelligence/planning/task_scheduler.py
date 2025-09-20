"""
Планировщик задач для AI-ассистента Лиза.
"""

import logging
import threading
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from queue import PriorityQueue, Empty
from concurrent.futures import ThreadPoolExecutor, Future


class TaskScheduler:
    """Планировщик задач для выполнения в заданное время или периодически."""

    def __init__(self, max_workers: int = 10):
        self.logger = logging.getLogger(__name__)

        # Очередь задач с приоритетом
        self.task_queue = PriorityQueue()

        # Флаг работы планировщика
        self.is_running = False

        # Поток выполнения задач
        self.scheduler_thread = None

        # Реестр зарегистрированных задач
        self.registered_tasks = {}

        # Пул потоков для выполнения задач
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Блокировка для безопасного доступа к задачам
        self.lock = threading.RLock()

    def add_task(self, task_id: str, task_func: Callable, schedule_time: datetime,
                priority: int = 0, args: tuple = (), kwargs: Dict[str, Any] = None,
                recurring: bool = False, interval: Optional[timedelta] = None) -> bool:
        """
        Добавление задачи в планировщик.

        Args:
            task_id: ID задачи
            task_func: Функция для выполнения
            schedule_time: Время выполнения
            priority: Приоритет задачи
            args: Аргументы функции
            kwargs: Именованные аргументы функции
            recurring: Флаг повторяющейся задачи
            interval: Интервал для повторяющихся задач

        Returns:
            True если задача добавлена успешно
        """
        if kwargs is None:
            kwargs = {}

        with self.lock:
            # Проверка конфликта ID
            if task_id in self.registered_tasks:
                self.logger.warning(f"Задача с ID {task_id} уже существует")
                return False

            # Создание задачи
            task = {
                'id': task_id,
                'function': task_func,
                'schedule_time': schedule_time,
                'priority': priority,
                'args': args,
                'kwargs': kwargs,
                'recurring': recurring,
                'interval': interval,
                'added_at': datetime.now()
            }

            # Добавление в очередь
            self.task_queue.put((priority, schedule_time.timestamp(), task_id, task))

            # Регистрация задачи
            self.registered_tasks[task_id] = task

            self.logger.info(f"Задача добавлена: {task_id} на {schedule_time}")
            return True

    def remove_task(self, task_id: str) -> bool:
        """
        Удаление задачи из планировщика.

        Args:
            task_id: ID задачи

        Returns:
            True если задача удалена успешно
        """
        with self.lock:
            if task_id not in self.registered_tasks:
                self.logger.warning(f"Задача с ID {task_id} не найдена")
                return False

            # Удаление из реестра
            del self.registered_tasks[task_id]

            # Создание новой очереди без удаленной задачи
            new_queue = PriorityQueue()
            tasks_kept = 0

            try:
                while True:
                    priority, timestamp, existing_task_id, task = self.task_queue.get_nowait()
                    if existing_task_id != task_id:
                        new_queue.put((priority, timestamp, existing_task_id, task))
                        tasks_kept += 1
            except Empty:
                pass

            # Замена старой очереди новой
            self.task_queue = new_queue
            self.logger.info(f"Задача удалена: {task_id}. Осталось задач: {tasks_kept}")
            return True

    def start(self):
        """Запуск планировщика задач."""
        if self.is_running:
            self.logger.warning("Планировщик уже запущен")
            return

        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()

        self.logger.info("Планировщик задач запущен")

    def stop(self):
        """Остановка планировщика задач."""
        self.is_running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)

        self.logger.info("Планировщик задач остановлен")

    def _scheduler_loop(self):
        """Основной цикл планировщика."""
        while self.is_running:
            try:
                current_time = datetime.now()

                # Временное хранилище для задач, которые еще не готовы
                pending_tasks = []

                with self.lock:
                    # Обработка всех задач в очереди
                    while not self.task_queue.empty():
                        try:
                            priority, timestamp, task_id, task = self.task_queue.get_nowait()

                            # Проверка актуальности задачи
                            if task_id not in self.registered_tasks:
                                continue  # Задача была удалена

                            if current_time >= task['schedule_time']:
                                # Задача готова к выполнению
                                self._execute_task(task)

                                # Для повторяющихся задач - перепланирование
                                if task['recurring'] and task['interval']:
                                    new_schedule_time = task['schedule_time'] + task['interval']
                                    new_task = task.copy()
                                    new_task['schedule_time'] = new_schedule_time

                                    # Обновление в реестре
                                    self.registered_tasks[task_id] = new_task
                                    # Добавление в очередь
                                    self.task_queue.put((priority, new_schedule_time.timestamp(), task_id, new_task))
                            else:
                                # Задача еще не готова
                                pending_tasks.append((priority, timestamp, task_id, task))

                        except Empty:
                            break

                    # Возврат неготовых задач в очередь
                    for task_data in pending_tasks:
                        self.task_queue.put(task_data)

                # Небольшая пауза перед следующей проверкой
                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Ошибка в цикле планировщика: {e}")
                time.sleep(1)  # Защита от бесконечного цикла ошибок

    def _execute_task(self, task: Dict[str, Any]):
        """Выполнение задачи в отдельном потоке."""
        try:
            self.logger.info(f"Выполнение задачи: {task['id']}")

            # Вызов функции задачи в отдельном потоке
            future = self.executor.submit(
                task['function'],
                *task['args'],
                **task['kwargs']
            )

            # Добавление обработчика для логирования результата
            future.add_done_callback(lambda f: self._task_done_callback(f, task['id']))

        except Exception as e:
            self.logger.error(f"Ошибка планирования задачи {task['id']}: {e}")

    def _task_done_callback(self, future: Future, task_id: str):
        """Обработчик завершения задачи."""
        try:
            result = future.result()
            self.logger.info(f"Задача выполнена: {task_id}. Результат: {result}")
        except Exception as e:
            self.logger.error(f"Ошибка выполнения задачи {task_id}: {e}")

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Получение списка ожидающих задач."""
        tasks = []

        with self.lock:
            # Создание временной очереди
            temp_queue = PriorityQueue()

            # Извлечение всех задач и их анализ
            try:
                while True:
                    priority, timestamp, task_id, task = self.task_queue.get_nowait()

                    # Добавление в результат, если задача актуальна
                    if task_id in self.registered_tasks:
                        tasks.append({
                            'id': task_id,
                            'schedule_time': task['schedule_time'],
                            'priority': task['priority'],
                            'recurring': task['recurring']
                        })

                    # Сохранение задачи во временной очереди
                    temp_queue.put((priority, timestamp, task_id, task))

            except Empty:
                pass

            # Восстановление оригинальной очереди
            self.task_queue = temp_queue

        return tasks

    def reschedule_task(self, task_id: str, new_time: datetime) -> bool:
        """
        Изменение времени выполнения задачи.

        Args:
            task_id: ID задачи
            new_time: Новое время выполнения

        Returns:
            True если время изменено успешно
        """
        with self.lock:
            if task_id not in self.registered_tasks:
                return False

            # Обновление времени в зарегистрированной задаче
            task = self.registered_tasks[task_id]
            task['schedule_time'] = new_time

            # Пересоздание очереди с обновленным временем
            new_queue = PriorityQueue()

            try:
                while True:
                    priority, timestamp, existing_task_id, existing_task = self.task_queue.get_nowait()
                    if existing_task_id == task_id:
                        # Замена задачи на обновленную версию
                        new_queue.put((priority, new_time.timestamp(), task_id, task))
                    else:
                        new_queue.put((priority, timestamp, existing_task_id, existing_task))
            except Empty:
                pass

            self.task_queue = new_queue
            self.logger.info(f"Задача перепланирована: {task_id} на {new_time}")
            return True

    def shutdown(self):
        """Корректное завершение работы планировщика."""
        self.stop()

        # Очистка очереди
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
            except Empty:
                break

        # Очистка реестра задач
        self.registered_tasks.clear()

        # Завершение работы пула потоков
        self.executor.shutdown(wait=True)

        self.logger.info("Планировщик задач завершил работу")