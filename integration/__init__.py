"""
Пакет интеграции с внешними системами для AI-ассистента Лиза.
"""

from .ci_cd.jenkins import JenkinsManager
from .ci_cd.gitlab import GitLabManager
from .ci_cd.github import GitHubManager

from .cloud.aws import AWSManager
from .cloud.azure import AzureManager
from .cloud.gcp import GCPManager

from .messaging.telegram import TelegramBot
from .messaging.email import EmailClient

__all__ = [
    'JenkinsManager', 'GitLabManager', 'GitHubManager',
    'AWSManager', 'AzureManager', 'GCPManager',
    'TelegramBot', 'EmailClient'
]