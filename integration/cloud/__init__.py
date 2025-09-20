"""
Пакет интеграции с облачными платформами для AI-ассистента Лиза.
"""

from .aws import AWSManager
from .azure import AzureManager
from .gcp import GCPManager

__all__ = ['AWSManager', 'AzureManager', 'GCPManager']