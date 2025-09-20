"""
Пакет интеграции с системами messaging для AI-ассистента Лиза.
"""

from .telegram import TelegramBot
from .email import EmailClient

__all__ = ['TelegramBot', 'EmailClient']