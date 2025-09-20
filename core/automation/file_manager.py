"""
Модуль управления файлами и файловой системой.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional, Union

class FileManager:
    """Менеджер управления файлами и файловой системой."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def list_files(self, directory: str, pattern: str = "*") -> List[Path]:
        """Получение списка файлов в директории."""
        try:
            path = Path(directory)
            if not path.exists():
                self.logger.error(f"Директория не существует: {directory}")
                return []

            return list(path.glob(pattern))
        except Exception as e:
            self.logger.error(f"Ошибка получения списка файлов: {e}")
            return []

    def create_directory(self, directory: str) -> bool:
        """Создание директории."""
        try:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка создания директории: {e}")
            return False

    def delete_directory(self, directory: str) -> bool:
        """Удаление директории."""
        try:
            path = Path(directory)
            if path.exists():
                shutil.rmtree(path)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка удаления директории: {e}")
            return False

    def copy_file(self, source: str, destination: str) -> bool:
        """Копирование файла."""
        try:
            src_path = Path(source)
            dst_path = Path(destination)

            if not src_path.exists():
                self.logger.error(f"Исходный файл не существует: {source}")
                return False

            shutil.copy2(src_path, dst_path)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка копирования файла: {e}")
            return False

    def move_file(self, source: str, destination: str) -> bool:
        """Перемещение файла."""
        try:
            src_path = Path(source)
            dst_path = Path(destination)

            if not src_path.exists():
                self.logger.error(f"Исходный файл не существует: {source}")
                return False

            shutil.move(str(src_path), str(dst_path))
            return True
        except Exception as e:
            self.logger.error(f"Ошибка перемещения файла: {e}")
            return False

    def delete_file(self, file_path: str) -> bool:
        """Удаление файла."""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка удаления файла: {e}")
            return False

    def read_file(self, file_path: str) -> Optional[str]:
        """Чтение содержимого файла."""
        try:
            path = Path(file_path)
            if not path.exists():
                self.logger.error(f"Файл не существует: {file_path}")
                return None

            return path.read_text(encoding='utf-8')
        except Exception as e:
            self.logger.error(f"Ошибка чтения файла: {e}")
            return None

    def write_file(self, file_path: str, content: str) -> bool:
        """Запись содержимого в файл."""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            self.logger.error(f"Ошибка записи файла: {e}")
            return False

    def file_exists(self, file_path: str) -> bool:
        """Проверка существования файла."""
        return Path(file_path).exists()

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """Получение информации о файле."""
        try:
            path = Path(file_path)
            if not path.exists():
                return None

            stat = path.stat()
            return {
                'size': stat.st_size,
                'modified_time': stat.st_mtime,
                'created_time': stat.st_ctime,
                'is_directory': path.is_dir(),
                'extension': path.suffix
            }
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о файле: {e}")
            return None