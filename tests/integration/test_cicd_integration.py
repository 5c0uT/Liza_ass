"""
Интеграционные тесты для CI/CD систем.
"""

import pytest
from unittest.mock import Mock, patch
from integration.ci_cd.jenkins import JenkinsManager
from integration.ci_cd.gitlab import GitLabManager
from integration.ci_cd.github import GitHubManager


class TestJenkinsIntegration:
    """Интеграционные тесты для Jenkins."""

    @pytest.fixture
    def jenkins_manager(self):
        return JenkinsManager("http://localhost:8080", "admin", "token")

    @patch('jenkinsapi.jenkins.Jenkins')
    def test_connect_jenkins(self, mock_jenkins, jenkins_manager):
        """Тест подключения к Jenkins."""
        mock_server = Mock()
        mock_jenkins.return_value = mock_server

        result = jenkins_manager.connect()
        assert result == True
        assert jenkins_manager.connection == mock_server

    @patch('jenkinsapi.jenkins.Jenkins')
    def test_run_job(self, mock_jenkins, jenkins_manager):
        """Тест запуска job в Jenkins."""
        mock_server = Mock()
        mock_job = Mock()
        mock_build = Mock()

        mock_jenkins.return_value = mock_server
        mock_server.__getitem__.return_value = mock_job
        mock_job.invoke.return_value = Mock()
        mock_job.invoke.return_value.get_build.return_value = mock_build
        mock_build.buildno = 123

        jenkins_manager.connect()
        result = jenkins_manager.run_job("test_job")

        assert result == 123
        mock_job.invoke.assert_called_once()

    @patch('jenkinsapi.jenkins.Jenkins')
    def test_get_job_status(self, mock_jenkins, jenkins_manager):
        """Тест получения статуса job в Jenkins."""
        mock_server = Mock()
        mock_job = Mock()
        mock_build = Mock()

        mock_jenkins.return_value = mock_server
        mock_server.__getitem__.return_value = mock_job
        mock_job.get_last_build.return_value = mock_build
        mock_build.buildno = 123
        mock_build.get_status.return_value = "SUCCESS"
        mock_build.get_build_url.return_value = "http://localhost:8080/job/test_job/123/"
        mock_build.get_duration.return_value = Mock(total_seconds=Mock(return_value=30.5))
        mock_build.get_timestamp.return_value = 1640995200

        jenkins_manager.connect()
        result = jenkins_manager.get_job_status("test_job")

        assert result is not None
        assert result['number'] == 123
        assert result['status'] == "SUCCESS"


class TestGitLabIntegration:
    """Интеграционные тесты для GitLab."""

    @pytest.fixture
    def gitlab_manager(self):
        return GitLabManager("https://gitlab.com", "token")

    @patch('gitlab.Gitlab')
    def test_connect_gitlab(self, mock_gitlab, gitlab_manager):
        """Тест подключения к GitLab."""
        mock_gl = Mock()
        mock_gitlab.return_value = mock_gl

        result = gitlab_manager.connect()
        assert result == True
        assert gitlab_manager.connection == mock_gl

    @patch('gitlab.Gitlab')
    def test_get_projects(self, mock_gitlab, gitlab_manager):
        """Тест получения проектов из GitLab."""
        mock_gl = Mock()
        mock_project = Mock()

        mock_gitlab.return_value = mock_gl
        mock_gl.projects.list.return_value = [mock_project]
        mock_project.id = 123
        mock_project.name = "test-project"
        mock_project.path = "test-project"
        mock_project.web_url = "https://gitlab.com/test-group/test-project"
        mock_project.visibility = "private"

        gitlab_manager.connect()
        result = gitlab_manager.get_projects()

        assert len(result) == 1
        assert result[0]['id'] == 123
        assert result[0]['name'] == "test-project"


class TestGitHubIntegration:
    """Интеграционные тесты для GitHub."""

    @pytest.fixture
    def github_manager(self):
        return GitHubManager("token")

    @patch('requests.request')
    def test_get_user_repos(self, mock_request, github_manager):
        """Тест получения репозиториев пользователя GitHub."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 123, "name": "test-repo", "full_name": "user/test-repo"}
        ]
        mock_request.return_value = mock_response

        result = github_manager.get_user_repos()

        assert len(result) == 1
        assert result[0]['id'] == 123
        assert result[0]['name'] == "test-repo"

    @patch('requests.request')
    def test_create_repo(self, mock_request, github_manager):
        """Тест создания репозитория в GitHub."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 123, "name": "new-repo", "html_url": "https://github.com/user/new-repo"
        }
        mock_request.return_value = mock_response

        result = github_manager.create_repo("new-repo", "Test repository")

        assert result is not None
        assert result['id'] == 123
        assert result['name'] == "new-repo"