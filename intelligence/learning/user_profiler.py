"""
Профилировщик пользователя для AI-ассистента Лиза.
"""

import logging
import json
import threading
import re
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import copy


class UserProfiler:
    """Профилировщик для создания и анализа профилей пользователей."""

    def __init__(self, profiles_dir: str = "data/profiles"):
        self.logger = logging.getLogger(__name__)
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(exist_ok=True)

        # Текущий профиль и блокировка для потокобезопасности
        self.current_profile = None
        self.lock = threading.RLock()

        # Кэш загруженных профилей
        self.profiles_cache = {}

        # Миграция профилей при необходимости
        self._migrate_old_profiles()

    def _migrate_old_profiles(self):
        """Миграция старых версий профилей при необходимости."""
        for profile_file in self.profiles_dir.glob("*.json"):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)

                # Проверка версии профиля и миграция при необходимости
                if 'version' not in profile_data:
                    profile_data = self._migrate_to_v1(profile_data)
                    with open(profile_file, 'w', encoding='utf-8') as f:
                        json.dump(profile_data, f, indent=2, ensure_ascii=False)
                    self.logger.info(f"Мигрирован профиль: {profile_file.name}")

            except Exception as e:
                self.logger.error(f"Ошибка миграции профиля {profile_file.name}: {e}")

    def _migrate_to_v1(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Миграция профиля до версии 1.0."""
        # Добавление поля версии
        profile_data['version'] = '1.0'

        # Добавление отсутствующих полей
        if 'learning_progress' not in profile_data:
            profile_data['learning_progress'] = {
                'completed_tasks': 0,
                'success_rate': 0.0,
                'learning_curve': []
            }

        return profile_data

    def create_profile(self, user_id: str, initial_data: Dict[str, Any] = None) -> bool:
        """
        Создание профиля пользователя.

        Args:
            user_id: ID пользователя
            initial_data: Начальные данные профиля

        Returns:
            True если профиль создан успешно
        """
        # Валидация user_id
        if not self._validate_user_id(user_id):
            self.logger.error(f"Некорректный ID пользователя: {user_id}")
            return False

        profile_path = self.profiles_dir / f"{user_id}.json"

        with self.lock:
            if profile_path.exists():
                self.logger.warning(f"Профиль уже существует: {user_id}")
                return False

            # Данные профиля по умолчанию
            profile_data = {
                'version': '1.0',
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'preferences': {
                    'language': 'ru',
                    'theme': 'dark',
                    'voice_speed': 1.0,
                    'auto_update': True,
                    'notifications': True,
                    'privacy_level': 'medium'
                },
                'behavior_patterns': {
                    'working_hours': {'start': '09:00', 'end': '18:00'},
                    'frequent_commands': [],
                    'preferred_apps': [],
                    'activity_patterns': {}
                },
                'skill_level': {
                    'programming': 0.5,
                    'system_administration': 0.5,
                    'automation': 0.5,
                    'data_analysis': 0.5,
                    'network': 0.5
                },
                'learning_progress': {
                    'completed_tasks': 0,
                    'success_rate': 0.0,
                    'learning_curve': [],
                    'skill_improvements': {}
                },
                'goals': {
                    'short_term': [],
                    'long_term': []
                }
            }

            # Обновление начальными данными
            if initial_data:
                profile_data = self._deep_update(profile_data, initial_data)

            # Сохранение профиля
            try:
                with open(profile_path, 'w', encoding='utf-8') as f:
                    json.dump(profile_data, f, indent=2, ensure_ascii=False)

                # Добавление в кэш
                self.profiles_cache[user_id] = profile_data
                self.logger.info(f"Профиль создан: {user_id}")
                return True

            except Exception as e:
                self.logger.error(f"Ошибка создания профиля: {e}")
                return False

    def _validate_user_id(self, user_id: str) -> bool:
        """Валидация ID пользователя."""
        # Проверка на пустую строку
        if not user_id or not user_id.strip():
            return False

        # Проверка на допустимые символы
        if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
            return False

        # Проверка длины
        if len(user_id) > 50:
            return False

        return True

    def load_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Загрузка профиля пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Данные профиля или None если не найден
        """
        # Проверка кэша
        if user_id in self.profiles_cache:
            return self.profiles_cache[user_id]

        profile_path = self.profiles_dir / f"{user_id}.json"

        if not profile_path.exists():
            self.logger.error(f"Профиль не найден: {user_id}")
            return None

        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)

            # Валидация загруженного профиля
            if not self._validate_profile(profile_data):
                self.logger.error(f"Профиль не прошел валидацию: {user_id}")
                return None

            # Сохранение в кэш
            with self.lock:
                self.profiles_cache[user_id] = profile_data

            return profile_data

        except Exception as e:
            self.logger.error(f"Ошибка загрузки профиля: {e}")
            return None

    def _validate_profile(self, profile_data: Dict[str, Any]) -> bool:
        """Валидация структуры профиля."""
        required_fields = ['user_id', 'created_at', 'updated_at', 'preferences']

        for field in required_fields:
            if field not in profile_data:
                return False

        # Проверка типа данных
        if not isinstance(profile_data.get('preferences', {}), dict):
            return False

        return True

    def update_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Обновление профиля пользователя.

        Args:
            user_id: ID пользователя
            updates: Данные для обновления

        Returns:
            True если профиль обновлен успешно
        """
        profile_data = self.load_profile(user_id)
        if not profile_data:
            return False

        # Глубокое обновление данных
        updated_profile = self._deep_update(profile_data, updates)
        updated_profile['updated_at'] = datetime.now().isoformat()

        # Сохранение обновленного профиля
        profile_path = self.profiles_dir / f"{user_id}.json"

        try:
            # Создание резервной копии
            self._create_backup(profile_path)

            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(updated_profile, f, indent=2, ensure_ascii=False)

            # Обновление кэша
            with self.lock:
                self.profiles_cache[user_id] = updated_profile

            self.logger.info(f"Профиль обновлен: {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка обновления профиля: {e}")
            # Восстановление из резервной копии при ошибке
            self._restore_backup(profile_path)
            return False

    def _deep_update(self, original: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """Глубокое обновление словаря."""
        result = copy.deepcopy(original)

        for key, value in updates.items():
            if (key in result and isinstance(result[key], dict) and
                isinstance(value, dict)):
                result[key] = self._deep_update(result[key], value)
            else:
                result[key] = value

        return result

    def _create_backup(self, profile_path: Path):
        """Создание резервной копии профиля."""
        if not profile_path.exists():
            return

        backup_path = profile_path.parent / f"{profile_path.name}.backup"

        try:
            with open(profile_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
        except Exception as e:
            self.logger.error(f"Ошибка создания резервной копии: {e}")

    def _restore_backup(self, profile_path: Path):
        """Восстановление профиля из резервной копии."""
        backup_path = profile_path.parent / f"{profile_path.name}.backup"

        if not backup_path.exists():
            return

        try:
            with open(backup_path, 'r', encoding='utf-8') as src:
                with open(profile_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())

            # Удаление резервной копии после восстановления
            backup_path.unlink()

        except Exception as e:
            self.logger.error(f"Ошибка восстановления из резервной копии: {e}")

    def track_command(self, user_id: str, command: str, success: bool,
                      execution_time: float, context: Dict[str, Any] = None):
        """
        Отслеживание выполнения команды для профиля.

        Args:
            user_id: ID пользователя
            command: Выполненная команда
            success: Успешность выполнения
            execution_time: Время выполнения
            context: Контекст выполнения
        """
        profile_data = self.load_profile(user_id)
        if not profile_data:
            # Создание профиля, если не существует
            if self.create_profile(user_id):
                profile_data = self.load_profile(user_id)
            else:
                return

        # Обновление frequent_commands
        frequent_commands = profile_data['behavior_patterns']['frequent_commands']

        # Поиск команды в списке
        command_entry = next((c for c in frequent_commands if c['command'] == command), None)

        if command_entry:
            command_entry['count'] += 1
            command_entry['last_used'] = datetime.now().isoformat()
            command_entry['success_rate'] = (
                    (command_entry['success_rate'] * (command_entry['count'] - 1) + success) /
                    command_entry['count']
            )
            command_entry['avg_time'] = (
                    (command_entry['avg_time'] * (command_entry['count'] - 1) + execution_time) /
                    command_entry['count']
            )
        else:
            frequent_commands.append({
                'command': command,
                'count': 1,
                'last_used': datetime.now().isoformat(),
                'success_rate': 1.0 if success else 0.0,
                'avg_time': execution_time,
                'context': context or {}
            })

        # Обновление learning_progress
        learning = profile_data['learning_progress']
        learning['completed_tasks'] += 1

        if learning['completed_tasks'] > 0:
            learning['success_rate'] = (
                    (learning['success_rate'] * (learning['completed_tasks'] - 1) + success) /
                    learning['completed_tasks']
            )

        # Добавление точки кривой обучения
        learning['learning_curve'].append({
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'time': execution_time,
            'command': command
        })

        # Обновление активности по времени суток
        self._update_activity_patterns(profile_data, command)

        # Сохранение обновленного профиля
        self.update_profile(user_id, profile_data)

    def _update_activity_patterns(self, profile_data: Dict[str, Any], command: str):
        """Обновление паттернов активности."""
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0 = Monday, 6 = Sunday

        activity_patterns = profile_data['behavior_patterns']['activity_patterns']

        # Инициализация структур данных при необходимости
        if 'by_hour' not in activity_patterns:
            activity_patterns['by_hour'] = {str(h): 0 for h in range(24)}
        if 'by_weekday' not in activity_patterns:
            activity_patterns['by_weekday'] = {str(d): 0 for d in range(7)}
        if 'command_frequency' not in activity_patterns:
            activity_patterns['command_frequency'] = {}

        # Обновление статистики
        activity_patterns['by_hour'][str(hour)] += 1
        activity_patterns['by_weekday'][str(weekday)] += 1

        if command in activity_patterns['command_frequency']:
            activity_patterns['command_frequency'][command] += 1
        else:
            activity_patterns['command_frequency'][command] = 1

    def get_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получение рекомендаций для пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список рекомендаций
        """
        profile_data = self.load_profile(user_id)
        if not profile_data:
            return []

        recommendations = []

        # Анализ frequent_commands для рекомендаций
        frequent_commands = profile_data['behavior_patterns']['frequent_commands']

        # Рекомендация на основе часто используемых команд
        for command in frequent_commands:
            if command['count'] > 5 and command['success_rate'] < 0.7:
                recommendations.append({
                    'type': 'improvement',
                    'message': f'Использование команды "{command["command"]}" можно улучшить',
                    'priority': 'medium',
                    'suggestion': 'Рассмотрите обучение или автоматизацию этой команды',
                    'context': {
                        'command': command['command'],
                        'success_rate': command['success_rate'],
                        'usage_count': command['count']
                    }
                })

        # Рекомендация на основе skill_level
        skills = profile_data['skill_level']
        for skill, level in skills.items():
            if level < 0.3:
                recommendations.append({
                    'type': 'learning',
                    'message': f'Рекомендуется улучшить навык: {skill}',
                    'priority': 'high',
                    'suggestion': f'Изучите материалы по {skill} или пройдите training',
                    'context': {
                        'skill': skill,
                        'current_level': level,
                        'target_level': 0.7
                    }
                })

        # Рекомендация на основе working_hours
        working_hours = profile_data['behavior_patterns']['working_hours']
        try:
            start_hour = int(working_hours['start'].split(':')[0])
            end_hour = int(working_hours['end'].split(':')[0])

            # Проверка на необычные рабочие часы
            if end_hour - start_hour > 10:
                recommendations.append({
                    'type': 'wellbeing',
                    'message': 'Обнаружены длинные рабочие часы',
                    'priority': 'medium',
                    'suggestion': 'Рассмотрите возможность более сбалансированного расписания',
                    'context': {
                        'start_hour': start_hour,
                        'end_hour': end_hour,
                        'duration': end_hour - start_hour
                    }
                })
        except (ValueError, KeyError):
            pass

        # Сортировка по приоритету
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recommendations.sort(key=lambda x: priority_order[x['priority']])

        return recommendations[:5]  # Возвращаем top-5 рекомендаций

    def detect_behavior_patterns(self, user_id: str) -> Dict[str, Any]:
        """
        Обнаружение поведенческих паттернов пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Обнаруженные паттерны
        """
        profile_data = self.load_profile(user_id)
        if not profile_data:
            return {}

        patterns = {
            'time_based': {},
            'command_sequences': [],
            'preferences': {},
            'anomalies': []
        }

        # Анализ временных паттернов
        frequent_commands = profile_data['behavior_patterns']['frequent_commands']
        for command in frequent_commands:
            last_used = datetime.fromisoformat(command['last_used'])
            hour = last_used.hour

            if hour not in patterns['time_based']:
                patterns['time_based'][hour] = []
            patterns['time_based'][hour].append(command['command'])

        # Анализ последовательностей команд
        learning_curve = profile_data['learning_progress']['learning_curve']
        if learning_curve:
            # Поиск часто повторяющихся последовательностей
            sequences = self._find_command_sequences(learning_curve)
            patterns['command_sequences'] = sequences

        # Обнаружение аномалий
        patterns['anomalies'] = self._detect_anomalies(profile_data)

        return patterns

    def _find_command_sequences(self, learning_curve: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Поиск часто повторяющихся последовательностей команд."""
        # Извлечение списка команд в порядке выполнения
        commands = [entry['command'] for entry in learning_curve]

        # Поиск последовательностей длиной 2-3 команды
        sequences = []
        sequence_lengths = [2, 3]

        for length in sequence_lengths:
            sequence_count = {}
            for i in range(len(commands) - length + 1):
                sequence = tuple(commands[i:i+length])
                if sequence in sequence_count:
                    sequence_count[sequence] += 1
                else:
                    sequence_count[sequence] = 1

            # Добавление последовательностей, которые встречаются хотя бы 3 раза
            for sequence, count in sequence_count.items():
                if count >= 3:
                    sequences.append({
                        'sequence': list(sequence),
                        'count': count,
                        'length': length
                    })

        return sequences

    def _detect_anomalies(self, profile_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Обнаружение аномалий в поведении пользователя."""
        anomalies = []

        # Проверка резких изменений в успешности выполнения команд
        learning_curve = profile_data['learning_progress']['learning_curve']
        if len(learning_curve) > 10:
            recent_success = [entry['success'] for entry in learning_curve[-5:]]
            previous_success = [entry['success'] for entry in learning_curve[-10:-5]]

            recent_success_rate = sum(recent_success) / len(recent_success)
            previous_success_rate = sum(previous_success) / len(previous_success)

            if abs(recent_success_rate - previous_success_rate) > 0.5:
                anomalies.append({
                    'type': 'success_rate_change',
                    'message': 'Обнаружено резкое изменение успешности выполнения команд',
                    'severity': 'medium',
                    'details': {
                        'previous_rate': previous_success_rate,
                        'current_rate': recent_success_rate,
                        'change': recent_success_rate - previous_success_rate
                    }
                })

        return anomalies

    def delete_profile(self, user_id: str) -> bool:
        """
        Удаление профиля пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            True если профиль удален успешно
        """
        profile_path = self.profiles_dir / f"{user_id}.json"

        if not profile_path.exists():
            self.logger.warning(f"Профиль не найден: {user_id}")
            return False

        try:
            # Создание резервной копии перед удалением
            backup_dir = self.profiles_dir / "deleted"
            backup_dir.mkdir(exist_ok=True)
            backup_path = backup_dir / f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(profile_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())

            # Удаление профиля
            profile_path.unlink()

            # Удаление из кэша
            with self.lock:
                if user_id in self.profiles_cache:
                    del self.profiles_cache[user_id]

            self.logger.info(f"Профиль удален: {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка удаления профиля: {e}")
            return False

    def list_profiles(self) -> List[str]:
        """
        Получение списка всех профилей.

        Returns:
            Список ID пользователей
        """
        profiles = []

        for profile_file in self.profiles_dir.glob("*.json"):
            if not profile_file.name.endswith('.backup'):
                profiles.append(profile_file.stem)

        return profiles

    def cleanup_old_data(self, max_age_days: int = 365) -> int:
        """
        Очистка устаревших данных из всех профилей.

        Args:
            max_age_days: Максимальный возраст данных в днях

        Returns:
            Количество очищенных профилей
        """
        cleaned_count = 0
        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        for user_id in self.list_profiles():
            profile_data = self.load_profile(user_id)
            if not profile_data:
                continue

            # Очистка старых записей learning_curve
            learning_curve = profile_data['learning_progress']['learning_curve']
            original_count = len(learning_curve)

            learning_curve[:] = [
                entry for entry in learning_curve
                if datetime.fromisoformat(entry['timestamp']) >= cutoff_date
            ]

            if len(learning_curve) < original_count:
                # Сохранение обновленного профиля
                if self.update_profile(user_id, profile_data):
                    cleaned_count += 1
                    self.logger.info(f"Очищен профиль: {user_id}, удалено записей: {original_count - len(learning_curve)}")

        return cleaned_count