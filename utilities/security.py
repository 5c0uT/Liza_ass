"""
Модуль безопасности для AI-ассистента Лиза.
"""

import logging
import hashlib
import hmac
import secrets
import string
from typing import Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os


class SecurityManager:
    """Менеджер безопасности для шифрования и хеширования."""

    def __init__(self, secret_key: Optional[str] = None):
        self.logger = logging.getLogger(__name__)

        # Генерация или использование предоставленного ключа
        if secret_key:
            self.secret_key = secret_key.encode()
        else:
            self.secret_key = Fernet.generate_key()

        # Инициализация Fernet для симметричного шифрования
        self.fernet = Fernet(self.secret_key)

    def encrypt_data(self, data: str) -> str:
        """
        Шифрование данных.

        Args:
            data: Данные для шифрования

        Returns:
            Зашифрованные данные в base64
        """
        try:
            if isinstance(data, str):
                data = data.encode()

            encrypted = self.fernet.encrypt(data)
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            self.logger.error(f"Ошибка шифрования данных: {e}")
            raise

    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Расшифрование данных.

        Args:
            encrypted_data: Зашифрованные данные в base64

        Returns:
            Расшифрованные данные
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            self.logger.error(f"Ошибка расшифрования данных: {e}")
            raise

    def hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Хеширование пароля с salt.

        Args:
            password: Пароль для хеширования
            salt: Salt (опционально, генерируется если не предоставлена)

        Returns:
            Кортеж (хеш, salt)
        """
        try:
            if salt is None:
                salt = self.generate_salt()

            # Использование PBKDF2 для хеширования
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt.encode(),
                iterations=100000,
            )

            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            return key.decode(), salt

        except Exception as e:
            self.logger.error(f"Ошибка хеширования пароля: {e}")
            raise

    def verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """
        Проверка пароля.

        Args:
            password: Пароль для проверки
            hashed_password: Хешированный пароль
            salt: Salt использованная при хешировании

        Returns:
            True если пароль верный
        """
        try:
            new_hash, _ = self.hash_password(password, salt)
            return hmac.compare_digest(new_hash, hashed_password)
        except Exception as e:
            self.logger.error(f"Ошибка проверки пароля: {e}")
            return False

    def generate_salt(self, length: int = 16) -> str:
        """Генерация cryptographically secure salt."""
        return secrets.token_hex(length)

    def generate_token(self, length: int = 32) -> str:
        """Генерация secure token."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def generate_api_key(self, prefix: str = "lisa") -> str:
        """Генерация API ключа."""
        token = self.generate_token(32)
        return f"{prefix}_{token}"

    def secure_delete(self, file_path: str, passes: int = 3) -> bool:
        """
        Безопасное удаление файла с перезаписью.

        Args:
            file_path: Путь к файлу
            passes: Количество проходов перезаписи

        Returns:
            True если файл успешно удален
        """
        try:
            if not os.path.exists(file_path):
                return False

            # Получение размера файла
            file_size = os.path.getsize(file_path)

            # Перезапись файла случайными данными
            with open(file_path, "wb") as file:
                for _ in range(passes):
                    file.write(os.urandom(file_size))
                    file.flush()
                    os.fsync(file.fileno())

            # Удаление файла
            os.remove(file_path)
            return True

        except Exception as e:
            self.logger.error(f"Ошибка безопасного удаления файла: {e}")
            return False

    def validate_input(self, input_str: str, max_length: int = 255,
                       allowed_chars: str = None) -> bool:
        """
        Валидация пользовательского ввода.

        Args:
            input_str: Строка для валидации
            max_length: Максимальная длина
            allowed_chars: Разрешенные символы (regex pattern)

        Returns:
            True если ввод валиден
        """
        if not input_str or len(input_str) > max_length:
            return False

        if allowed_chars:
            import re
            if not re.match(allowed_chars, input_str):
                return False

        # Проверка на потенциально опасные конструкции
        dangerous_patterns = [
            ";", "--", "/*", "*/", "@@",
            "char(", "nchar(", "exec(", "xp_", "sp_"
        ]

        if any(pattern in input_str.lower() for pattern in dangerous_patterns):
            return False

        return True