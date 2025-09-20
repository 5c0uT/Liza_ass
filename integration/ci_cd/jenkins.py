"""
Модуль интеграции с Jenkins.
"""

import logging
from typing import Dict, Any, Optional, List
from jenkinsapi.jenkins import Jenkins
from jenkinsapi.build import Build


class JenkinsManager:
    """Менеджер интеграции с Jenkins."""

    def __init__(self, url: str, username: str, api_token: str, timeout: int = 30):
        self.logger = logging.getLogger(__name__)
        self.url = url
        self.username = username
        self.api_token = api_token
        self.timeout = timeout
        self.connection = None

    def connect(self) -> bool:
        """Подключение к серверу Jenkins."""
        try:
            self.connection = Jenkins(
                self.url,
                username=self.username,
                password=self.api_token,
                timeout=self.timeout
            )
            self.logger.info(f"Успешное подключение к Jenkins: {self.url}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка подключения к Jenkins: {e}")
            return False

    def get_jobs(self) -> List[Dict[str, Any]]:
        """Получение списка всех jobs."""
        if not self.connection:
            if not self.connect():
                return []

        try:
            jobs = []
            for job_name, job in self.connection.get_jobs():
                jobs.append({
                    'name': job_name,
                    'url': job.url,
                    'description': job.get_description(),
                    'is_running': job.is_running(),
                    'is_enabled': job.is_enabled()
                })
            return jobs
        except Exception as e:
            self.logger.error(f"Ошибка получения списка jobs: {e}")
            return []

    def run_job(self, job_name: str, parameters: Optional[Dict[str, str]] = None) -> Optional[int]:
        """Запуск job."""
        if not self.connection:
            if not self.connect():
                return None

        try:
            job = self.connection[job_name]
            queue_item = job.invoke(build_params=parameters or {})

            # Ожидание начала build
            build = queue_item.get_build()
            return build.buildno
        except Exception as e:
            self.logger.error(f"Ошибка запуска job {job_name}: {e}")
            return None

    def get_job_status(self, job_name: str, build_number: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Получение статуса job."""
        if not self.connection:
            if not self.connect():
                return None

        try:
            job = self.connection[job_name]

            if build_number:
                build = job.get_build(build_number)
            else:
                build = job.get_last_build()

            return {
                'number': build.buildno,
                'status': build.get_status(),
                'url': build.get_build_url(),
                'duration': build.get_duration().total_seconds(),
                'timestamp': build.get_timestamp(),
                'result': build.get_result()
            }
        except Exception as e:
            self.logger.error(f"Ошибка получения статуса job {job_name}: {e}")
            return None

    def get_build_console_output(self, job_name: str, build_number: int) -> Optional[str]:
        """Получение console output билда."""
        if not self.connection:
            if not self.connect():
                return None

        try:
            job = self.connection[job_name]
            build = job.get_build(build_number)
            return build.get_console()
        except Exception as e:
            self.logger.error(f"Ошибка получения console output: {e}")
            return None

    def stop_build(self, job_name: str, build_number: int) -> bool:
        """Остановка билда."""
        if not self.connection:
            if not self.connect():
                return False

        try:
            job = self.connection[job_name]
            build = job.get_build(build_number)
            build.stop()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка остановки билда: {e}")
            return False