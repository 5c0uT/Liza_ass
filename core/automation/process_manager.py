"""
Модуль управления процессами и системными ресурсами.
"""

import logging
import psutil
import subprocess
from typing import List, Optional, Dict, Any


class ProcessManager:
    """Менеджер управления процессами и системными ресурсами."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_running_processes(self) -> List[Dict[str, Any]]:
        """Получение списка запущенных процессов."""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            return processes
        except Exception as e:
            self.logger.error(f"Ошибка получения списка процессов: {e}")
            return []

    def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """Получение информации о конкретном процессе."""
        try:
            process = psutil.Process(pid)
            return {
                'pid': process.pid,
                'name': process.name(),
                'status': process.status(),
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'create_time': process.create_time(),
                'exe': process.exe(),
                'cmdline': process.cmdline(),
                'username': process.username()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.logger.error(f"Ошибка получения информации о процессе {pid}: {e}")
            return None

    def start_process(self, command: str, args: List[str] = None,
                      wait: bool = False) -> Optional[int]:
        """Запуск нового процесса."""
        try:
            if args is None:
                args = []

            if wait:
                result = subprocess.run([command] + args, capture_output=True, text=True)
                return result.returncode
            else:
                process = subprocess.Popen([command] + args)
                return process.pid

        except Exception as e:
            self.logger.error(f"Ошибка запуска процесса {command}: {e}")
            return None

    def terminate_process(self, pid: int) -> bool:
        """Завершение процесса."""
        try:
            process = psutil.Process(pid)
            process.terminate()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.logger.error(f"Ошибка завершения процесса {pid}: {e}")
            return False

    def kill_process(self, pid: int) -> bool:
        """Принудительное завершение процесса."""
        try:
            process = psutil.Process(pid)
            process.kill()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.logger.error(f"Ошибка принудительного завершения процесса {pid}: {e}")
            return False

    def get_process_children(self, pid: int) -> List[Dict[str, Any]]:
        """Получение дочерних процессов."""
        try:
            process = psutil.Process(pid)
            children = []
            for child in process.children(recursive=True):
                children.append({
                    'pid': child.pid,
                    'name': child.name(),
                    'status': child.status()
                })
            return children
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.logger.error(f"Ошибка получения дочерних процессов {pid}: {e}")
            return []

    def get_system_resources(self) -> Dict[str, Any]:
        """Получение информации о системных ресурсах."""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': dict(psutil.virtual_memory()._asdict()),
                'disk_usage': dict(psutil.disk_usage('/')._asdict()),
                'boot_time': psutil.boot_time(),
                'users': [dict(user._asdict()) for user in psutil.users()]
            }
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о системных ресурсах: {e}")
            return {}