"""
Модуль интеграции с GitLab для AI-ассистента Лиза.
"""

import logging
import gitlab
from typing import Dict, Any, List, Optional


class GitLabManager:
    """Менеджер для работы с GitLab API."""

    def __init__(self, url: str, private_token: str):
        self.logger = logging.getLogger(__name__)

        self.url = url
        self.private_token = private_token
        self.connection = None

    def connect(self) -> bool:
        """Подключение к GitLab."""
        try:
            self.connection = gitlab.Gitlab(self.url, private_token=self.private_token)
            self.connection.auth()
            self.logger.info("Успешное подключение к GitLab")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка подключения к GitLab: {e}")
            return False

    def get_projects(self, owned: bool = True) -> List[Dict[str, Any]]:
        """Получение списка проектов."""
        if not self.connection:
            if not self.connect():
                return []

        try:
            if owned:
                projects = self.connection.projects.list(owned=True)
            else:
                projects = self.connection.projects.list()

            return [{
                'id': project.id,
                'name': project.name,
                'path': project.path,
                'web_url': project.web_url,
                'visibility': project.visibility
            } for project in projects]
        except Exception as e:
            self.logger.error(f"Ошибка получения списка проектов: {e}")
            return []

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о проекте."""
        if not self.connection:
            if not self.connect():
                return None

        try:
            project = self.connection.projects.get(project_id)
            return {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'web_url': project.web_url,
                'ssh_url': project.ssh_url_to_repo,
                'http_url': project.http_url_to_repo,
                'visibility': project.visibility
            }
        except Exception as e:
            self.logger.error(f"Ошибка получения проекта {project_id}: {e}")
            return None

    def create_project(self, name: str, description: str = "",
                       visibility: str = "private") -> Optional[Dict[str, Any]]:
        """Создание нового проекта."""
        if not self.connection:
            if not self.connect():
                return None

        try:
            project = self.connection.projects.create({
                'name': name,
                'description': description,
                'visibility': visibility
            })

            return {
                'id': project.id,
                'name': project.name,
                'web_url': project.web_url
            }
        except Exception as e:
            self.logger.error(f"Ошибка создания проекта: {e}")
            return None

    def get_pipelines(self, project_id: str, status: str = None) -> List[Dict[str, Any]]:
        """Получение списка pipelines проекта."""
        if not self.connection:
            if not self.connect():
                return []

        try:
            project = self.connection.projects.get(project_id)

            if status:
                pipelines = project.pipelines.list(status=status)
            else:
                pipelines = project.pipelines.list()

            return [{
                'id': pipeline.id,
                'status': pipeline.status,
                'ref': pipeline.ref,
                'sha': pipeline.sha,
                'web_url': pipeline.web_url,
                'created_at': pipeline.created_at
            } for pipeline in pipelines]
        except Exception as e:
            self.logger.error(f"Ошибка получения pipelines проекта {project_id}: {e}")
            return []

    def trigger_pipeline(self, project_id: str, ref: str = "main",
                         variables: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
        """
        Запуск pipeline.

        Args:
            project_id: ID проекта
            ref: Ветка или тег
            variables: Переменные pipeline

        Returns:
            Запущенный pipeline
        """
        if not self.connection:
            if not self.connect():
                return None

        try:
            project = self.connection.projects.get(project_id)

            pipeline = project.pipelines.create({
                'ref': ref,
                'variables': variables or {}
            })

            return {
                'id': pipeline.id,
                'status': pipeline.status,
                'web_url': pipeline.web_url
            }
        except Exception as e:
            self.logger.error(f"Ошибка запуска pipeline: {e}")
            return None

    def get_merge_requests(self, project_id: str, state: str = "opened") -> List[Dict[str, Any]]:
        """Получение списка merge requests проекта."""
        if not self.connection:
            if not self.connect():
                return []

        try:
            project = self.connection.projects.get(project_id)
            mrs = project.mergerequests.list(state=state)

            return [{
                'id': mr.id,
                'title': mr.title,
                'state': mr.state,
                'author': mr.author['username'],
                'web_url': mr.web_url,
                'created_at': mr.created_at
            } for mr in mrs]
        except Exception as e:
            self.logger.error(f"Ошибка получения merge requests проекта {project_id}: {e}")
            return []

    def create_merge_request(self, project_id: str, source_branch: str,
                             target_branch: str, title: str, description: str = "") -> Optional[Dict[str, Any]]:
        """
        Создание merge request.

        Args:
            project_id: ID проекта
            source_branch: Исходная ветка
            target_branch: Целевая ветка
            title: Заголовок MR
            description: Описание MR

        Returns:
            Созданный merge request
        """
        if not self.connection:
            if not self.connect():
                return None

        try:
            project = self.connection.projects.get(project_id)

            mr = project.mergerequests.create({
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': title,
                'description': description
            })

            return {
                'id': mr.id,
                'title': mr.title,
                'web_url': mr.web_url
            }
        except Exception as e:
            self.logger.error(f"Ошибка создания merge request: {e}")
            return None