"""
Фикстуры конфигурации для тестов AI-ассистента Лиза.
"""

import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_config_dir():
    """Создание временной директории для конфигураций."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_config_file(temp_config_dir):
    """Создание sample конфигурационного файла."""
    config_data = """
    [general]
    name = "Test Lisa"
    version = "1.0"
    language = "ru"

    [voice]
    model_size = "base"
    energy_threshold = 1000

    [ml]
    fusion_net_hidden_dim = 512
    """

    config_file = temp_config_dir / "test_config.toml"
    config_file.write_text(config_data)
    return config_file


@pytest.fixture
def sample_telegram_config(temp_config_dir):
    """Создание sample конфигурации Telegram."""
    config_data = """
    [default]
    enabled = true
    token = "test_token"
    chat_id = "12345"
    alert_level = "ERROR"
    """

    config_file = temp_config_dir / "telegrams.toml"
    config_file.write_text(config_data)
    return config_file


@pytest.fixture
def sample_ci_cd_config(temp_config_dir):
    """Создание sample конфигурации CI/CD."""
    config_data = """
    [jenkins.default]
    url = "http://localhost:8080"
    username = "admin"
    api_token = "test_token"

    [gitlab.default]
    url = "https://gitlab.com"
    private_token = "test_token"
    """

    config_file = temp_config_dir / "ci_cd.toml"
    config_file.write_text(config_data)
    return config_file


@pytest.fixture
def sample_workflow_config(temp_config_dir):
    """Создание sample workflow конфигурации."""
    workflow_data = {
        "name": "Test Workflow",
        "description": "Test workflow for automation",
        "nodes": [
            {
                "type": "command",
                "id": "node1",
                "position": [100, 100],
                "properties": {
                    "command": "echo hello"
                }
            }
        ],
        "connections": []
    }

    import json
    workflow_file = temp_config_dir / "test_workflow.json"
    workflow_file.write_text(json.dumps(workflow_data, indent=2))
    return workflow_file