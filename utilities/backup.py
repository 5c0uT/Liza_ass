"""
Модуль резервного копирования для AI-ассистента Лиза.
"""

import logging
import zipfile
import tarfile
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import shutil


class BackupManager:
    """Менеджер резервного копирования данных и конфигураций."""

    def __init__(self, backup_dir: str = "backups", max_backups: int = 30):
        self.logger = logging.getLogger(__name__)

        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups

        # Создание директории для бэкапов если не существует
        self.backup_dir.mkdir(exist_ok=True)

        # Добавление атрибутов для автоматического бэкапа
        self.auto_backup_enabled = False
        self.scheduler_thread = None

    def create_backup(self, sources: List[str], backup_name: Optional[str] = None,
                      compression: str = "zip") -> Optional[Path]:
        """
        Создание резервной копии указанных источников.

        Args:
            sources: Список путей для резервного копирования
            backup_name: Имя backup файла (опционально)
            compression: Тип сжатия (zip, tar, tar.gz)

        Returns:
            Путь к созданному backup файлу
        """
        if backup_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"

        backup_path = self.backup_dir / f"{backup_name}.{compression}"

        try:
            if compression == "zip":
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for source in sources:
                        source_path = Path(source)
                        if source_path.exists():
                            if source_path.is_file():
                                zipf.write(source_path, source_path.name)
                            else:
                                for file in source_path.rglob('*'):
                                    if file.is_file():
                                        arcname = file.relative_to(source_path.parent)
                                        zipf.write(file, arcname)
                        else:
                            self.logger.warning(f"Источник не существует: {source}")

            elif compression in ["tar", "tar.gz"]:
                mode = "w:gz" if compression == "tar.gz" else "w"
                with tarfile.open(backup_path, mode) as tar:
                    for source in sources:
                        source_path = Path(source)
                        if source_path.exists():
                            tar.add(source_path, arcname=source_path.name)
                        else:
                            self.logger.warning(f"Источник не существует: {source}")

            else:
                self.logger.error(f"Неизвестный тип сжатия: {compression}")
                return None

            self.logger.info(f"Резервная копия создана: {backup_path}")

            # Очистка старых бэкапов
            self._cleanup_old_backups()

            return backup_path

        except Exception as e:
            self.logger.error(f"Ошибка создания резервной копии: {e}")
            return None

    def restore_backup(self, backup_path: str, target_dir: str = ".",
                       overwrite: bool = False) -> bool:
        """
        Восстановление из резервной копии.

        Args:
            backup_path: Путь к backup файлу
            target_dir: Целевая директория для восстановления
            overwrite: Перезапись существующих файлов

        Returns:
            True если восстановление прошло успешно
        """
        backup_path = Path(backup_path)
        target_dir = Path(target_dir)

        if not backup_path.exists():
            self.logger.error(f"Backup файл не существует: {backup_path}")
            return False

        try:
            if backup_path.suffix == ".zip":
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(target_dir)

            elif backup_path.suffix in [".tar", ".gz", ".tgz"]:
                with tarfile.open(backup_path, 'r:*') as tar:
                    tar.extractall(target_dir)

            else:
                self.logger.error(f"Неизвестный формат backup: {backup_path.suffix}")
                return False

            self.logger.info(f"Восстановление из backup завершено: {backup_path}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка восстановления из backup: {e}")
            return False

    def _cleanup_old_backups(self):
        """Очистка старых backup файлов."""
        try:
            # Получение списка backup файлов
            backup_files = list(self.backup_dir.glob("backup_*.*"))

            # Сортировка по дате создания
            backup_files.sort(key=lambda x: x.stat().st_mtime)

            # Удаление старых файлов если превышен лимит
            if len(backup_files) > self.max_backups:
                files_to_delete = backup_files[:-self.max_backups]
                for file in files_to_delete:
                    file.unlink()
                    self.logger.info(f"Удален старый backup: {file}")

        except Exception as e:
            self.logger.error(f"Ошибка очистки старых backup: {e}")

    def list_backups(self) -> List[Dict[str, Any]]:
        """Получение списка доступных backup."""
        backups = []

        for file in self.backup_dir.glob("backup_*.*"):
            stat = file.stat()
            backups.append({
                'name': file.name,
                'path': str(file),
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_mtime),
                'format': file.suffix[1:]  # без точки
            })

        # Сортировка по дате создания (новые first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        return backups

    def create_config_backup(self, config_dir: str = "config") -> Optional[Path]:
        """
        Создание резервной копии конфигураций.

        Args:
            config_dir: Директория с конфигурациями

        Returns:
            Путь к созданному backup файлу
        """
        config_files = []
        config_path = Path(config_dir)

        if config_path.exists():
            for file in config_path.glob("*.toml"):
                config_files.append(str(file))
            for file in config_path.glob("*.json"):
                config_files.append(str(file))
            for file in config_path.glob("*.conf"):
                config_files.append(str(file))

        if config_files:
            return self.create_backup(config_files, "config_backup", "zip")
        else:
            self.logger.warning("Не найдены файлы конфигурации для backup")
            return None

    def create_knowledge_backup(self, knowledge_dir: str = "knowledge") -> Optional[Path]:
        """
        Создание резервной копии базы знаний.

        Args:
            knowledge_dir: Директория с базой знаний

        Returns:
            Путь к созданному backup файлу
        """
        knowledge_path = Path(knowledge_dir)

        if knowledge_path.exists():
            # Поиск всех файлов базы знаний
            knowledge_files = []
            for ext in ['*.db', '*.json', '*.pkl', '*.bin']:
                knowledge_files.extend([str(f) for f in knowledge_path.rglob(ext)])

            if knowledge_files:
                return self.create_backup(knowledge_files, "knowledge_backup", "zip")

        self.logger.warning("Не найдены файлы базы знаний для backup")
        return None

    def schedule_auto_backup(self, interval_hours: int = 24,
                             backup_types: List[str] = None):
        """
        Настройка автоматического резервного копирования.

        Args:
            interval_hours: Интервал в часах
            backup_types: Типы backup (config, knowledge, all)
        """
        if backup_types is None:
            backup_types = ['config', 'knowledge']

        # Проверка валидности типов бэкапов
        valid_types = ['config', 'knowledge', 'all']
        for btype in backup_types:
            if btype not in valid_types:
                self.logger.warning(f"Неизвестный тип бэкапа: {btype}. Используются типы по умолчанию.")
                backup_types = ['config', 'knowledge']
                break

        self.logger.info(f"Настроено автоматическое резервное копирование каждые {interval_hours} часов")

        # Создание планировщика
        import schedule
        import time
        import threading

        def backup_job():
            """Задача для выполнения резервного копирования."""
            self.logger.info("Запуск автоматического резервного copying...")

            backup_files = []

            # Создание бэкапов в зависимости от указанных типов
            if 'all' in backup_types or 'config' in backup_types:
                config_backup = self.create_config_backup()
                if config_backup:
                    backup_files.append(config_backup)
                    self.logger.info(f"Создан бэкап конфигурации: {config_backup}")

            if 'all' in backup_types or 'knowledge' in backup_types:
                knowledge_backup = self.create_knowledge_backup()
                if knowledge_backup:
                    backup_files.append(knowledge_backup)
                    self.logger.info(f"Создан бэкап базы знаний: {knowledge_backup}")

            # Логирование результатов
            if backup_files:
                self.logger.info(f"Автоматическое резервное копирование завершено. Создано {len(backup_files)} файлов.")
            else:
                self.logger.warning("Автоматическое резервное копирование не создало файлов.")

        # Настройка расписания
        schedule.every(interval_hours).hours.do(backup_job)

        # Функция для запуска планировщика в отдельном потоке
        def run_scheduler():
            while self.auto_backup_enabled:
                schedule.run_pending()
                time.sleep(60)  # Проверка каждую минуту

        # Запуск планировщика в отдельном потоке
        self.auto_backup_enabled = True
        self.scheduler_thread = threading.Thread(target=run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()

        # Немедленный запуск первой задачи
        backup_job()