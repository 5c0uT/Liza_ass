"""
Модуль интеграции с GitHub для AI-ассистента Лиза.
"""

import logging
import requests
from typing import Dict, Any, List, Optional


class GitHubManager:
    """Менеджер для работы с GitHub API."""

    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        self.logger = logging.getLogger(__name__)

        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Выполнение HTTP запроса к GitHub API."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data
            )

            if response.status_code in [200, 201]:
                return response.json()
            else:
                self.logger.error(f"Ошибка GitHub API: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"Ошибка выполнения запроса к GitHub: {e}")
            return None

    def get_user_repos(self, username: str = None) -> List[Dict[str, Any]]:
        """Получение списка репозиториев пользователя."""
        if username:
            endpoint = f"/users/{username}/repos"
        else:
            endpoint = "/user/repos"

        response = self._make_request("GET", endpoint)
        return response or []

    def get_repo(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Получение информации о репозитории."""
        endpoint = f"/repos/{owner}/{repo}"
        return self._make_request("GET", endpoint)

    def create_repo(self, name: str, description: str = "",
                    private: bool = False) -> Optional[Dict[str, Any]]:
        """Создание нового репозитория."""
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": True
        }

        return self._make_request("POST", "/user/repos", data)

    def get_workflows(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Получение списка workflows репозитория."""
        endpoint = f"/repos/{owner}/{repo}/actions/workflows"
        response = self._make_request("GET", endpoint)
        return response.get('workflows', []) if response else []

    def trigger_workflow(self, owner: str, repo: str, workflow_id: str,
                         ref: str = "main", inputs: Dict = None) -> bool:
        """
        Запуск workflow.

        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            workflow_id: ID workflow
            ref: Ветка или тег
            inputs: Входные параметры

        Returns:
            True если workflow запущен успешно
        """
        endpoint = f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"

        data = {
            "ref": ref
        }

        if inputs:
            data["inputs"] = inputs

        response = self._make_request("POST", endpoint, data)
        return response is not None

    def get_workflow_runs(self, owner: str, repo: str, workflow_id: str = None,
                          branch: str = None, status: str = None) -> List[Dict[str, Any]]:
        """
        Получение списка workflow runs.

        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            workflow_id: ID workflow (опционально)
            branch: Ветка (опционально)
            status: Статус (опционально)

        Returns:
            Список workflow runs
        """
        endpoint = f"/repos/{owner}/{repo}/actions/runs"

        # Добавление параметров
        params = {}
        if workflow_id:
            params['workflow_id'] = workflow_id
        if branch:
            params['branch'] = branch
        if status:
            params['status'] = status

        response = self._make_request("GET", endpoint, params)
        return response.get('workflow_runs', []) if response else []

    def get_pull_requests(self, owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """
        Получение списка pull requests.

        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            state: Статус PR (open, closed, all)

        Returns:
            Список pull requests
        """
        endpoint = f"/repos/{owner}/{repo}/pulls"
        params = {"state": state}

        response = self._make_request("GET", endpoint, params)
        return response or []

    def create_pull_request(self, owner: str, repo: str, title: str,
                            head: str, base: str, body: str = "") -> Optional[Dict[str, Any]]:
        """
        Создание pull request.

        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            title: Заголовок PR
            head: Ветка с изменениями
            base: Целевая ветка
            body: Описание PR

        Returns:
            Созданный pull request
        """
        endpoint = f"/repos/{owner}/{repo}/pulls"
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body
        }

        return self._make_request("POST", endpoint, data)