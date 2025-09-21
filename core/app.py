"""
Главный класс приложения Лиза.
"""

import logging
import re
import os
import subprocess
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
import webbrowser
import requests

# Пытаемся импортировать голосовой движок, используем заглушку при ошибке
try:
    from core.voice_input import VoiceInputEngine
except ImportError as e:
    logging.warning(f"Голосовой движок недоступен: {e}")
    from core.voice_input_stub import VoiceInputEngine

from core.tts import TTSEngine
from core.automation import AutomationManager
from core.gui.main_window import MainWindow
from ml.inference.engine import InferenceEngine
from intelligence.planning import TaskScheduler
from knowledge.vector_db import VectorDatabase

class LisaApp(QObject):
    """Основной класс приложения Лиза."""

    # Сигналы для взаимодействия с GUI
    voice_command_received = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    command_executed = pyqtSignal(str, bool)  # command, success

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.is_running = False

        # Инициализация компонентов
        self.voice_engine = None
        self.tts_engine = None
        self.automation_manager = None
        self.inference_engine = None
        self.task_scheduler = None
        self.vector_db = None
        self.gui = None

        # Состояние ассистента
        self.settings = {
            "volume": 50,
            "language": "ru",
            "theme": "light",
            "notifications": True
        }

        # История команд
        self.command_history = []

        # Кэш путей приложений
        self.app_paths_cache = {}

    def initialize(self) -> bool:
        """Инициализация всех компонентов приложения."""
        try:
            self.logger.info("Инициализация компонентов приложения...")

            # Инициализация движков голоса
            self.voice_engine = VoiceInputEngine()
            self.tts_engine = TTSEngine()

            # Инициализация менеджера автоматизации
            self.automation_manager = AutomationManager()

            # Инициализация ML компонентов
            self.inference_engine = InferenceEngine()

            # Инициализация планировщика задач
            self.task_scheduler = TaskScheduler()

            # Инициализация базы знаний
            self.vector_db = VectorDatabase()

            # Загрузка кэша путей приложений
            self._load_app_paths_cache()

            # Подключение сигналов
            self.voice_engine.command_received.connect(self._handle_voice_command)

            self.logger.info("Все компоненты успешно инициализированы")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка инициализации приложения: {e}")
            return False

    def _load_app_paths_cache(self):
        """Загрузка кэша путей приложений из файла."""
        try:
            cache_file = "data/app_paths_cache.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.app_paths_cache = json.load(f)
                self.logger.info(f"Загружено {len(self.app_paths_cache)} путей приложений из кэша")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки кэша путей приложений: {e}")

    def _save_app_paths_cache(self):
        """Сохранение кэша путей приложений в файл."""
        try:
            os.makedirs("data", exist_ok=True)
            cache_file = "data/app_paths_cache.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.app_paths_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения кэша путей приложений: {e}")

    def _find_application(self, app_name: str) -> Optional[str]:
        """
        Поиск приложения на компьютере.
        Возвращает путь к исполняемому файлу или None если не найдено.
        """
        try:
            # Проверяем кэш сначала
            if app_name.lower() in self.app_paths_cache:
                cached_path = self.app_paths_cache[app_name.lower()]
                if os.path.exists(cached_path):
                    return cached_path

            # Известные расположения приложений
            search_paths = [
                os.environ.get('ProgramFiles', 'C:\\Program Files'),
                os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'),
                os.environ.get('LOCALAPPDATA', ''),
                os.environ.get('APPDATA', ''),
                os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local'),
                os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Roaming'),
            ]

            # Расширения для поиска
            extensions = ['.exe', '.bat', '.cmd', '.lnk', '.msi']

            # Поиск в известных расположениях
            for search_path in search_paths:
                if not search_path or not os.path.exists(search_path):
                    continue

                try:
                    for root, dirs, files in os.walk(search_path):
                        for file in files:
                            # Проверяем совпадение имени файла
                            file_lower = file.lower()
                            app_name_lower = app_name.lower()

                            # Ищем точное совпадение или частичное
                            if (app_name_lower in file_lower or
                                    file_lower.startswith(app_name_lower) or
                                    file_lower.endswith(app_name_lower)):

                                # Проверяем расширение
                                if any(file_lower.endswith(ext) for ext in extensions):
                                    full_path = os.path.join(root, file)

                                    # Сохраняем в кэш
                                    self.app_paths_cache[app_name_lower] = full_path
                                    self._save_app_paths_cache()

                                    # Сохраняем в векторную БД
                                    self.vector_db.add_documents(
                                        collection_name="applications",
                                        documents=[f"Приложение {app_name} расположено по пути {full_path}"],
                                        ids=[f"app_{app_name_lower}"],
                                        metadatas=[{
                                            "name": app_name,
                                            "path": full_path,
                                            "type": "application",
                                            "found_date": datetime.now().isoformat()
                                        }]
                                    )

                                    return full_path
                except Exception as e:
                    self.logger.warning(f"Ошибка поиска в {search_path}: {e}")
                    continue

            # Поиск через системные команды (для Linux/Mac)
            if os.name != 'nt':
                try:
                    result = subprocess.run(['which', app_name],
                                            capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        path = result.stdout.strip()
                        if os.path.exists(path):
                            # Сохраняем в кэш и БД
                            app_name_lower = app_name.lower()
                            self.app_paths_cache[app_name_lower] = path
                            self._save_app_paths_cache()

                            self.vector_db.add_documents(
                                collection_name="applications",
                                documents=[f"Приложение {app_name} расположено по пути {path}"],
                                ids=[f"app_{app_name_lower}"],
                                metadatas=[{
                                    "name": app_name,
                                    "path": path,
                                    "type": "application",
                                    "found_date": datetime.now().isoformat()
                                }]
                            )

                            return path
                except Exception as e:
                    self.logger.warning(f"Ошибка поиска через which: {e}")

            return None

        except Exception as e:
            self.logger.error(f"Ошибка поиска приложения {app_name}: {e}")
            return None

    def _handle_voice_command(self, command: str):
        """Обработка полученной голосовой команды."""
        self.logger.debug(f"Получена команда: {command}")
        self.voice_command_received.emit(command)
        self.command_history.append({"command": command, "timestamp": datetime.now()})

        # Сначала пробуем простой парсер
        simple_intent = self._simple_command_parser(command)
        if simple_intent['action'] != 'unknown':
            self._execute_intent(simple_intent, command)
            return

        # Затем обработка через ML движок
        intent = self.inference_engine.process_command(command)
        self._execute_intent(intent, command)

    def _simple_command_parser(self, command: str) -> Dict[str, Any]:
        """Простой парсер команд на основе ключевых слов."""
        command_lower = command.lower()

        # 1. Информационные запросы
        if re.search(r'(какая|какой|сколько|когда|где|кто|что|как).*(погода|температура)', command_lower):
            location = self._extract_location(command)
            return {
                'action': 'get_weather',
                'parameters': {'location': location},
                'confidence': 0.9
            }

        elif re.search(r'(который час|сколько времени|время)', command_lower):
            return {
                'action': 'get_time',
                'parameters': {},
                'confidence': 0.9
            }

        elif re.search(r'(какая дата|какое число|дата)', command_lower):
            return {
                'action': 'get_date',
                'parameters': {},
                'confidence': 0.9
            }

        elif re.search(r'(найди|поиск|ищи|найти).*(в интернете|в сети)', command_lower):
            query = re.sub(r'.*(найди|поиск|ищи|найти).*(в интернете|в сети)', '', command_lower).strip()
            return {
                'action': 'web_search',
                'parameters': {'query': query},
                'confidence': 0.8
            }

        elif re.search(r'(определи|что значит|что такое)', command_lower):
            term = re.sub(r'.*(определи|что значит|что такое)', '', command_lower).strip()
            return {
                'action': 'get_definition',
                'parameters': {'term': term},
                'confidence': 0.8
            }

        # 2. Управленческие команды
        elif re.search(r'(открой|запусти|открыть|запустить)', command_lower):
            app_name = re.sub(r'.*(открой|запусти|открыть|запустить)', '', command_lower).strip()
            return {
                'action': 'open_application',
                'parameters': {'name': app_name},
                'confidence': 0.9
            }

        elif re.search(r'(закрой|закрыть|останови|остановить)', command_lower):
            app_name = re.sub(r'.*(закрой|закрыть|останови|остановить)', '', command_lower).strip()
            return {
                'action': 'close_application',
                'parameters': {'name': app_name},
                'confidence': 0.9
            }

        elif re.search(r'(громкость|звук|volume)', command_lower):
            if re.search(r'(увеличь|прибавь|больше)', command_lower):
                return {
                    'action': 'increase_volume',
                    'parameters': {'amount': 10},
                    'confidence': 0.8
                }
            elif re.search(r'(уменьши|убавь|меньше)', command_lower):
                return {
                    'action': 'decrease_volume',
                    'parameters': {'amount': 10},
                    'confidence': 0.8
                }
            else:
                # Попытка извлечь числовое значение
                numbers = re.findall(r'\d+', command_lower)
                if numbers:
                    return {
                        'action': 'set_volume',
                        'parameters': {'level': int(numbers[0])},
                        'confidence': 0.7
                    }

        elif re.search(r'(перезагрузись|перезапустись|restart)', command_lower):
            return {
                'action': 'restart_assistant',
                'parameters': {},
                'confidence': 0.9
            }

        elif re.search(r'(выключись|отключись|shutdown)', command_lower):
            return {
                'action': 'shutdown_assistant',
                'parameters': {},
                'confidence': 0.9
            }

        # 3. Творческие команды
        elif re.search(r'(напиши|создай|сгенерируй).*(код|программу)', command_lower):
            description = re.sub(r'.*(напиши|создай|сгенерируй).*(код|программу)', '', command_lower).strip()
            return {
                'action': 'generate_code',
                'parameters': {'description': description},
                'confidence': 0.8
            }

        elif re.search(r'(напиши|создай|сгенерируй).*(текст|историю|рассказ|статью)', command_lower):
            prompt = re.sub(r'.*(напиши|создай|сгенерируй).*(текст|историю|рассказ|статью)', '', command_lower).strip()
            return {
                'action': 'generate_text',
                'parameters': {'prompt': prompt, 'length': 200},
                'confidence': 0.8
            }

        elif re.search(r'(нарисуй|создай|сгенерируй).*(изображение|картинку|рисунок)', command_lower):
            description = re.sub(r'.*(нарисуй|создай|сгенерируй).*(изображение|картинку|рисунок)', '', command_lower).strip()
            return {
                'action': 'generate_image',
                'parameters': {'description': description},
                'confidence': 0.8
            }

        # 4. Коммуникационные команды
        elif re.search(r'(напиши|отправь).*(сообщение|письмо|sms)', command_lower):
            # Извлечение получателя и сообщения
            parts = re.split(r'(напиши|отправь).*(сообщение|письмо|sms)', command_lower)
            if len(parts) > 3:
                recipient_text = parts[3]
                # Простая эвристика для извлечения получателя
                if 'маме' in recipient_text or 'mom' in recipient_text:
                    recipient = 'мама'
                elif 'папе' in recipient_text or 'dad' in recipient_text:
                    recipient = 'папа'
                else:
                    recipient = 'неизвестный'

                message = re.sub(r'.*(маме|папе|мама|папа)', '', recipient_text).strip()

                return {
                    'action': 'send_message',
                    'parameters': {'recipient': recipient, 'message': message},
                    'confidence': 0.7
                }

        elif re.search(r'(позвони|позвонить|call)', command_lower):
            recipient = re.sub(r'.*(позвони|позвонить|call)', '', command_lower).strip()
            return {
                'action': 'make_call',
                'parameters': {'recipient': recipient},
                'confidence': 0.8
            }

        elif re.search(r'(создай|добавь).*(событие|встречу|напоминание)', command_lower):
            # Упрощенный парсинг для создания событий
            return {
                'action': 'create_event',
                'parameters': {'title': 'Новое событие', 'datetime': datetime.now() + timedelta(hours=1)},
                'confidence': 0.7
            }

        # 5. Образовательные команды
        elif re.search(r'(объясни|расскажи|что такое).*(концепт|концепция|понятие)', command_lower):
            concept = re.sub(r'.*(объясни|расскажи|что такое).*(концепт|концепция|понятие)', '', command_lower).strip()
            return {
                'action': 'explain_concept',
                'parameters': {'concept': concept, 'level': 'beginner'},
                'confidence': 0.8
            }

        elif re.search(r'(научи|обучи|покажи).*(навык|умение)', command_lower):
            skill = re.sub(r'.*(научи|обучи|покажи).*(навык|умение)', '', command_lower).strip()
            return {
                'action': 'teach_skill',
                'parameters': {'skill': skill},
                'confidence': 0.8
            }

        # 6. Развлекательные команды
        elif re.search(r'(расскажи|скажи).*(анекдот|шутку)', command_lower):
            return {
                'action': 'tell_joke',
                'parameters': {'category': 'general'},
                'confidence': 0.9
            }

        elif re.search(r'(включи|запусти|поиграй).*(музыку|песню)', command_lower):
            query = re.sub(r'.*(включи|запусти|поиграй).*(музыку|песню)', '', command_lower).strip()
            return {
                'action': 'play_music',
                'parameters': {'query': query},
                'confidence': 0.8
            }

        elif re.search(r'(включи|запусти|покажи).*(фильм|кино|видео)', command_lower):
            query = re.sub(r'.*(включи|запусти|покажи).*(фильм|кино|видео)', '', command_lower).strip()
            return {
                'action': 'play_video',
                'parameters': {'query': query},
                'confidence': 0.8
            }

        # 7. Навигационные команды
        elif re.search(r'(где|как добраться|маршрут|навигация)', command_lower):
            location = self._extract_location(command)
            return {
                'action': 'navigate_to',
                'parameters': {'destination': location},
                'confidence': 0.8
            }

        elif re.search(r'(найди|ищи|поиск).*(место|локацию|ресторан|кафе|магазин)', command_lower):
            query = re.sub(r'.*(найди|ищи|поиск).*(место|локацию|ресторан|кафе|магазин)', '', command_lower).strip()
            return {
                'action': 'find_place',
                'parameters': {'query': query},
                'confidence': 0.8
            }

        # 8. Команды для работы с файлами
        elif re.search(r'(создай|сделай).*(файл|документ)', command_lower):
            filename = re.sub(r'.*(создай|сделай).*(файл|документ)', '', command_lower).strip()
            return {
                'action': 'create_file',
                'parameters': {'filename': filename, 'content': ''},
                'confidence': 0.8
            }

        elif re.search(r'(открой|покажи).*(файл|документ)', command_lower):
            filename = re.sub(r'.*(открой|покажи).*(файл|документ)', '', command_lower).strip()
            return {
                'action': 'open_file',
                'parameters': {'filename': filename},
                'confidence': 0.8
            }

        elif re.search(r'(сохрани|запиши).*(файл|документ)', command_lower):
            # Упрощенный парсинг для сохранения файлов
            return {
                'action': 'save_file',
                'parameters': {'filename': 'документ.txt', 'content': ''},
                'confidence': 0.7
            }

        # 9. Команды для работы с приложениями
        elif re.search(r'(установи|инсталлируй).*(приложение|программу)', command_lower):
            app_name = re.sub(r'.*(установи|инсталлируй).*(приложение|программу)', '', command_lower).strip()
            return {
                'action': 'install_application',
                'parameters': {'name': app_name},
                'confidence': 0.8
            }

        elif re.search(r'(удали|убери).*(приложение|программу)', command_lower):
            app_name = re.sub(r'.*(удали|убери).*(приложение|программу)', '', command_lower).strip()
            return {
                'action': 'uninstall_application',
                'parameters': {'name': app_name},
                'confidence': 0.8
            }

        # 10. Команды для самоанализа и рефлексии
        elif re.search(r'(как|какие).*(ты|у тебя).*(дела|настроение)', command_lower):
            return {
                'action': 'report_status',
                'parameters': {},
                'confidence': 0.9
            }

        elif re.search(r'(что|какие).*(ты|умеешь|можешь)', command_lower):
            return {
                'action': 'list_capabilities',
                'parameters': {},
                'confidence': 0.9
            }

        elif re.search(r'(история|журнал).*(команд)', command_lower):
            return {
                'action': 'show_history',
                'parameters': {'count': 10},
                'confidence': 0.8
            }

        # 11. Команды для выполнения сложных задач
        elif re.search(r'(спланируй|организуй).*(мероприятие|событие)', command_lower):
            # Упрощенный парсинг для планирования мероприятий
            return {
                'action': 'plan_event',
                'parameters': {'title': 'Мероприятие', 'date': datetime.now() + timedelta(days=7)},
                'confidence': 0.7
            }

        elif re.search(r'(управляй|контролируй).*(проектом|задачей)', command_lower):
            # Упрощенный парсинг для управления проектами
            return {
                'action': 'manage_project',
                'parameters': {'name': 'Проект', 'action': 'start'},
                'confidence': 0.7
            }

        # 12. Команды, связанные с безопасностью и конфиденциальностью
        elif re.search(r'(заблокируй|защити).*(устройство|компьютер)', command_lower):
            return {
                'action': 'lock_device',
                'parameters': {},
                'confidence': 0.9
            }

        elif re.search(r'(проверь|сканируй).*(безопасность|вирусы)', command_lower):
            return {
                'action': 'scan_security',
                'parameters': {},
                'confidence': 0.8
            }

        # Неизвестная команда
        return {
            'action': 'unknown',
            'parameters': {},
            'confidence': 0.0
        }

    def _extract_location(self, command: str) -> str:
        """Извлечение локации из команды."""
        command_lower = command.lower()

        # Список возможных локаций
        locations = ['москва', 'санкт-петербург', 'нью-йорк', 'лондон', 'париж', 'берлин',
                    'токио', 'пекин', 'сеул', 'сидней', 'киев', 'минск', 'казань', 'екатеринбург']

        for location in locations:
            if location in command_lower:
                return location

        # Если локация не найдена, возвращаем по умолчанию
        return 'москва'

    def _execute_intent(self, intent: Dict[str, Any], original_command: str):
        """Выполнение намерения, определенного ML моделью или парсером."""
        try:
            action = intent.get('action')
            parameters = intent.get('parameters', {})
            confidence = intent.get('confidence', 0.0)

            self.logger.info(f"Выполнение действия: {action} с параметрами: {parameters} (уверенность: {confidence})")

            # 1. Информационные запросы
            if action == "get_weather":
                self._get_weather(parameters.get('location', 'москва'))

            elif action == "get_time":
                self._get_time()

            elif action == "get_date":
                self._get_date()

            elif action == "web_search":
                self._web_search(parameters.get('query', ''))

            elif action == "get_definition":
                self._get_definition(parameters.get('term', ''))

            elif action == "get_news":
                self._get_news(parameters.get('category', 'general'), parameters.get('count', 5))

            elif action == "get_stock_price":
                self._get_stock_price(parameters.get('symbol', 'AAPL'))

            elif action == "get_currency_rate":
                self._get_currency_rate(
                    parameters.get('from_currency', 'USD'),
                    parameters.get('to_currency', 'RUB')
                )

            # 2. Управленческие команды
            elif action == "open_application":
                self._open_application(parameters.get('name', ''))

            elif action == "close_application":
                self._close_application(parameters.get('name', ''))

            elif action == "set_volume":
                self._set_volume(parameters.get('level', 50))

            elif action == "increase_volume":
                self._increase_volume(parameters.get('amount', 10))

            elif action == "decrease_volume":
                self._decrease_volume(parameters.get('amount', 10))

            elif action == "set_language":
                self._set_language(parameters.get('language', 'ru'))

            elif action == "set_theme":
                self._set_theme(parameters.get('theme', 'dark'))

            elif action == "restart_assistant":
                self._restart_assistant()

            elif action == "shutdown_assistant":
                self._shutdown_assistant()

            # 3. Творческие команды
            elif action == "generate_code":
                self._generate_code(parameters.get('description', ''))

            elif action == "generate_text":
                self._generate_text(
                    parameters.get('prompt', ''),
                    parameters.get('length', 200)
                )

            elif action == "generate_image":
                self._generate_image(parameters.get('description', ''))

            elif action == "generate_music":
                self._generate_music(
                    parameters.get('genre', 'classical'),
                    parameters.get('duration', 60)
                )

            # 4. Коммуникационные команды
            elif action == "send_message":
                self._send_message(
                    parameters.get('recipient', ''),
                    parameters.get('message', '')
                )

            elif action == "make_call":
                self._make_call(parameters.get('recipient', ''))

            elif action == "read_messages":
                self._read_messages(parameters.get('count', 10))

            elif action == "create_event":
                self._create_event(
                    parameters.get('title', 'Событие'),
                    parameters.get('datetime', datetime.now() + timedelta(hours=1))
                )

            elif action == "cancel_event":
                self._cancel_event(parameters.get('title', ''))

            # 5. Образовательные команды
            elif action == "explain_concept":
                self._explain_concept(
                    parameters.get('concept', ''),
                    parameters.get('level', 'beginner')
                )

            elif action == "teach_skill":
                self._teach_skill(
                    parameters.get('skill', ''),
                    parameters.get('duration', 30)
                )

            elif action == "quiz":
                self._quiz(
                    parameters.get('topic', 'general'),
                    parameters.get('difficulty', 'medium')
                )

            # 6. Развлекательные команды
            elif action == "tell_joke":
                self._tell_joke(parameters.get('category', 'general'))

            elif action == "play_game":
                self._play_game(parameters.get('game', ''))

            elif action == "play_music":
                self._play_music(parameters.get('query', ''))

            elif action == "play_radio":
                self._play_radio(parameters.get('station', ''))

            elif action == "watch_movie":
                self._watch_movie(parameters.get('title', ''))

            # 7. Навигационные команды
            elif action == "find_location":
                self._find_location(
                    parameters.get('query', ''),
                    parameters.get('location', '')
                )

            elif action == "get_directions":
                self._get_directions(
                    parameters.get('from', ''),
                    parameters.get('to', ''),
                    parameters.get('mode', 'driving')
                )

            elif action == "get_traffic_info":
                self._get_traffic_info(parameters.get('route', ''))

            # 8. Команды для работы с файлами
            elif action == "create_file":
                self._create_file(
                    parameters.get('name', ''),
                    parameters.get('content', '')
                )

            elif action == "read_file":
                self._read_file(parameters.get('path', ''))

            elif action == "write_file":
                self._write_file(
                    parameters.get('path', ''),
                    parameters.get('content', '')
                )

            elif action == "delete_file":
                self._delete_file(parameters.get('path', ''))

            elif action == "organize_files":
                self._organize_files(
                    parameters.get('directory', ''),
                    parameters.get('method', 'type')
                )

            # 9. Команды для работы с приложениями
            elif action == "install_application":
                self._install_application(parameters.get('name', ''))

            elif action == "uninstall_application":
                self._uninstall_application(parameters.get('name', ''))

            elif action == "search_in_application":
                self._search_in_application(
                    parameters.get('application', ''),
                    parameters.get('query', '')
                )

            # 10. Команды для самоанализа и рефлексии
            elif action == "get_usage_stats":
                self._get_usage_stats(parameters.get('period', 'week'))

            elif action == "get_behavior_report":
                self._get_behavior_report()

            elif action == "provide_feedback":
                self._provide_feedback(parameters.get('feedback', ''))

            # 11. Команды для выполнения сложных задач
            elif action == "plan_event":
                self._plan_event(
                    parameters.get('event_type', ''),
                    parameters.get('date', ''),
                    parameters.get('guests', 0)
                )

            elif action == "manage_project":
                self._manage_project(
                    parameters.get('project', ''),
                    parameters.get('action', ''),
                    parameters.get('deadline', '')
                )

            elif action == "solve_problem":
                self._solve_problem(parameters.get('problem', ''))

            # 12. Команды, связанные с безопасностью и конфиденциальностью
            elif action == "lock_device":
                self._lock_device()

            elif action == "unlock_device":
                self._unlock_device()

            elif action == "encrypt_file":
                self._encrypt_file(parameters.get('path', ''))

            elif action == "decrypt_file":
                self._decrypt_file(parameters.get('path', ''))

            elif action == "change_password":
                self._change_password(
                    parameters.get('service', ''),
                    parameters.get('new_password', '')
                )

            # 13. Системные команды ассистента
            elif action == "report_status":
                self._report_status()

            elif action == "list_capabilities":
                self._list_capabilities()

            elif action == "show_history":
                self._show_history(parameters.get('count', 10))

            # Неизвестная команда
            else:
                self.logger.warning(f"Неизвестное действие: {action}")
                self.tts_engine.speak("Извините, я не поняла команду")
                self.command_executed.emit(original_command, False)

        except Exception as e:
            self.logger.error(f"Ошибка выполнения команды: {e}")
            self.tts_engine.speak("Произошла ошибка при выполнении команды")
            self.command_executed.emit(original_command, False)

    # Реализации всех методов команд

    # 1. Информационные запросы
    def _get_weather(self, location: str):
        """Получение информации о погоде."""
        try:
            # Здесь должен быть API запрос к сервису погоды
            # Временная заглушка
            weather_info = f"Погода в {location}: 20°C, солнечно"
            self.tts_engine.speak(weather_info)
            self.command_executed.emit(f"погода в {location}", True)
        except Exception as e:
            self.logger.error(f"Ошибка получения погоды: {e}")
            self.tts_engine.speak("Не удалось получить информацию о погоде")
            self.command_executed.emit(f"погода в {location}", False)

    def _get_time(self):
        """Получение текущего времени."""
        try:
            current_time = datetime.now().strftime("%H:%M")
            self.tts_engine.speak(f"Сейчас {current_time}")
            self.command_executed.emit("который час", True)
        except Exception as e:
            self.logger.error(f"Ошибка получения времени: {e}")
            self.tts_engine.speak("Не удалось получить время")
            self.command_executed.emit("который час", False)

    def _get_date(self):
        """Получение текущей даты."""
        try:
            current_date = datetime.now().strftime("%d %B %Y")
            self.tts_engine.speak(f"Сегодня {current_date}")
            self.command_executed.emit("какая дата", True)
        except Exception as e:
            self.logger.error(f"Ошибка получения даты: {e}")
            self.tts_engine.speak("Не удалось получить дату")
            self.command_executed.emit("какая дата", False)

    def _web_search(self, query: str):
        """Поиск в интернете."""
        try:
            search_url = f"https://www.google.com/search?q={query}"
            webbrowser.open(search_url)
            self.tts_engine.speak(f"Ищу {query} в интернете")
            self.command_executed.emit(f"найди {query}", True)
        except Exception as e:
            self.logger.error(f"Ошибка поиска в интернете: {e}")
            self.tts_engine.speak("Не удалось выполнить поиск")
            self.command_executed.emit(f"найди {query}", False)

    def _get_definition(self, term: str):
        """Получение определения термина."""
        try:
            # Здесь должен быть API запрос к словарю или Википедии
            # Временная заглушка
            definition = f"{term} - это термин, который требует дополнительного объяснения"
            self.tts_engine.speak(definition)
            self.command_executed.emit(f"определи {term}", True)
        except Exception as e:
            self.logger.error(f"Ошибка получения определения: {e}")
            self.tts_engine.speak("Не удалось найти определение")
            self.command_executed.emit(f"определи {term}", False)

    # 2. Управленческие команды
    def _open_application(self, name: str):
        """Открытие приложения с поиском по всему компьютеру."""
        try:
            # Сначала проверяем известные приложения
            known_apps = {
                'браузер': 'chrome.exe',
                'chrome': 'chrome.exe',
                'firefox': 'firefox.exe',
                'word': 'winword.exe',
                'excel': 'excel.exe',
                'steam': 'steam.exe',
                'проводник': 'explorer.exe',
                'калькулятор': 'calc.exe',
                'блокнот': 'notepad.exe',
                'paint': 'mspaint.exe'
            }

            # Проверяем известные приложения
            if name.lower() in known_apps:
                app_path = known_apps[name.lower()]
                subprocess.Popen(app_path, shell=True)
                self.tts_engine.speak(f"Открываю {name}")
                self.command_executed.emit(f"открой {name}", True)
                return

            # Ищем приложение в системе
            app_path = self._find_application(name)

            if app_path:
                # Запускаем приложение
                if os.name == 'nt':  # Windows
                    if app_path.endswith('.lnk'):
                        # Для ярлыков используем специальную команду
                        subprocess.Popen(['cmd', '/c', 'start', '', app_path], shell=True)
                    else:
                        subprocess.Popen(app_path, shell=True)
                else:  # Linux/Mac
                    subprocess.Popen([app_path], shell=True)

                self.tts_engine.speak(f"Открываю {name}")
                self.command_executed.emit(f"открой {name}", True)
            else:
                self.tts_engine.speak(f"Не удалось найти приложение {name}")
                self.command_executed.emit(f"открой {name}", False)

        except Exception as e:
            self.logger.error(f"Ошибка открытия приложения: {e}")
            self.tts_engine.speak(f"Не удалось открыть {name}")
            self.command_executed.emit(f"открой {name}", False)

    def _set_volume(self, level: int):
        """Установка уровня громкости."""
        try:
            # Здесь должен быть код для управления громкостью системы
            # Временная заглушка
            self.settings['volume'] = level
            self.tts_engine.speak(f"Громкость установлена на {level}%")
            self.command_executed.emit(f"громкость {level}", True)
        except Exception as e:
            self.logger.error(f"Ошибка установки громкости: {e}")
            self.tts_engine.speak("Не удалось установить громкость")
            self.command_executed.emit(f"громкость {level}", False)

    # 3. Творческие команды
    def _generate_code(self, description: str):
        """Генерация кода."""
        try:
            # Используем ML движок для генерации кода
            code = self.inference_engine.generate_code(description)
            self.automation_manager.insert_text(code)
            self.tts_engine.speak("Код сгенерирован и вставлен")
            self.command_executed.emit(f"сгенерируй код {description}", True)
        except Exception as e:
            self.logger.error(f"Ошибка генерации кода: {e}")
            self.tts_engine.speak("Не удалось сгенерировать код")
            self.command_executed.emit(f"сгенерируй код {description}", False)

    # 4. Коммуникационные команды
    def _send_message(self, recipient: str, message: str):
        """Отправка сообщения."""
        try:
            # Здесь должна быть интеграция с мессенджерами или email
            # Временная заглушка
            self.tts_engine.speak(f"Отправляю сообщение {recipient}: {message}")
            self.command_executed.emit(f"отправь сообщение {recipient}", True)
        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения: {e}")
            self.tts_engine.speak("Не удалось отправить сообщение")
            self.command_executed.emit(f"отправь сообщение {recipient}", False)

    # 5. Образовательные команды
    def _explain_concept(self, concept: str, level: str):
        """Объяснение концепции."""
        try:
            # Используем ML движок или базу знаний для объяснения
            explanation = self.inference_engine.explain_concept(concept, level)
            self.tts_engine.speak(explanation)
            self.command_executed.emit(f"объясни {concept}", True)
        except Exception as e:
            self.logger.error(f"Ошибка объяснения концепции: {e}")
            self.tts_engine.speak("Не удалось объяснить эту концепцию")
            self.command_executed.emit(f"объясни {concept}", False)

    # 6. Развлекательные команды
    def _tell_joke(self, category: str):
        """Рассказывание анекдота."""
        try:
            # Здесь должен быть API запрос к сервису анекдотов
            # Временная заглушка
            jokes = {
                'general': "Почему программисты путают Хэллоуин и Рождество? Потому что Oct 31 == Dec 25!",
                'programming': "Сколько программистов нужно, чтобы вкрутить лампочку? Ни одного, это hardware проблема!",
                'science': "Почему ученые не доверяют атомам? Потому что они все выдумывают!"
            }

            joke = jokes.get(category, jokes['general'])
            self.tts_engine.speak(joke)
            self.command_executed.emit("расскажи анекдот", True)
        except Exception as e:
            self.logger.error(f"Ошибка рассказа анекдота: {e}")
            self.tts_engine.speak("Не удалось найти анекдот")
            self.command_executed.emit("расскажи анекдот", False)

    # 10. Команды для самоанализа и рефлексии
    def _report_status(self):
        """Отчет о статусе ассистента."""
        try:
            status = f"Я работаю нормально. Громкость: {self.settings['volume']}%. Язык: {self.settings['language']}. Выполнено команд: {len(self.command_history)}"
            self.tts_engine.speak(status)
            self.command_executed.emit("как дела", True)
        except Exception as e:
            self.logger.error(f"Ошибка отчета статуса: {e}")
            self.tts_engine.speak("Не удалось сформировать отчет о статусе")
            self.command_executed.emit("как дела", False)

    def _list_capabilities(self):
        """Перечисление возможностей ассистента."""
        try:
            capabilities = """
                Я могу: отвечать на вопросы, искать информацию в интернете, открывать приложения,
                управлять громкостью, генерировать текст и код, отправлять сообщения, рассказывать анекдоты,
                работать с файлами, управлять задачами и многое другое. Спросите что-нибудь!
            """
            self.tts_engine.speak(capabilities)
            self.command_executed.emit("что ты умеешь", True)
        except Exception as e:
            self.logger.error(f"Ошибка перечисления возможностей: {e}")
            self.tts_engine.speak("Не удалось перечислить возможности")
            self.command_executed.emit("что ты умеешь", False)

    # 1. Информационные запросы (продолжение)
    def _get_news(self, category: str, count: int):
        """Получение новостей."""
        try:
            # Здесь должен быть API запрос к новостному сервису
            # Временная заглушка
            news = f"Вот последние новости из категории {category}: Новость 1, Новость 2, Новость 3"
            self.tts_engine.speak(news)
            self.command_executed.emit(f"новости {category}", True)
        except Exception as e:
            self.logger.error(f"Ошибка получения новостей: {e}")
            self.tts_engine.speak("Не удалось получить новости")
            self.command_executed.emit(f"новости {category}", False)

    def _get_stock_price(self, symbol: str):
        """Получение цены акций."""
        try:
            # Здесь должен быть API запрос к финансовому сервису
            # Временная заглушка
            price = f"Цена акций {symbol}: 150 долларов"
            self.tts_engine.speak(price)
            self.command_executed.emit(f"цена акций {symbol}", True)
        except Exception as e:
            self.logger.error(f"Ошибка получения цены акций: {e}")
            self.tts_engine.speak("Не удалось получить цену акций")
            self.command_executed.emit(f"цена акций {symbol}", False)

    def _get_currency_rate(self, from_currency: str, to_currency: str):
        """Получение курса валют."""
        try:
            # Здесь должен быть API запрос к финансовому сервису
            # Временная заглушка
            rate = f"Курс {from_currency} к {to_currency}: 75 рублей"
            self.tts_engine.speak(rate)
            self.command_executed.emit(f"курс {from_currency} {to_currency}", True)
        except Exception as e:
            self.logger.error(f"Ошибка получения курса валют: {e}")
            self.tts_engine.speak("Не удалось получить курс валют")
            self.command_executed.emit(f"курс {from_currency} {to_currency}", False)

    # 2. Управленческие команды (продолжение)
    def _close_application(self, name: str):
        """Закрытие приложения."""
        try:
            # Сопоставление названий с процессами приложений
            process_map = {
                'браузер': 'chrome.exe',
                'chrome': 'chrome.exe',
                'firefox': 'firefox.exe',
                'word': 'winword.exe',
                'excel': 'excel.exe',
                'steam': 'steam.exe',
                'проводник': 'explorer.exe',
                'калькулятор': 'calc.exe'
            }

            process_name = process_map.get(name.lower(), name)
            os.system(f"taskkill /f /im {process_name}")
            self.tts_engine.speak(f"Закрываю {name}")
            self.command_executed.emit(f"закрой {name}", True)
        except Exception as e:
            self.logger.error(f"Ошибка закрытия приложения: {e}")
            self.tts_engine.speak(f"Не удалось закрыть {name}")
            self.command_executed.emit(f"закрой {name}", False)

    def _increase_volume(self, amount: int):
        """Увеличение громкости."""
        try:
            # Здесь должен быть код для увеличения громкости системы
            # Временная заглушка
            new_volume = min(100, self.settings['volume'] + amount)
            self.settings['volume'] = new_volume
            self.tts_engine.speak(f"Громкость увеличена до {new_volume}%")
            self.command_executed.emit("увеличь громкость", True)
        except Exception as e:
            self.logger.error(f"Ошибка увеличения громкости: {e}")
            self.tts_engine.speak("Не удалось увеличить громкость")
            self.command_executed.emit("увеличь громкость", False)

    def _decrease_volume(self, amount: int):
        """Уменьшение громкости."""
        try:
            # Здесь должен быть код для уменьшения громкости системы
            # Временная заглушка
            new_volume = max(0, self.settings['volume'] - amount)
            self.settings['volume'] = new_volume
            self.tts_engine.speak(f"Громкость уменьшена до {new_volume}%")
            self.command_executed.emit("уменьши громкость", True)
        except Exception as e:
            self.logger.error(f"Ошибка уменьшения громкости: {e}")
            self.tts_engine.speak("Не удалось уменьшить громкость")
            self.command_executed.emit("уменьши громкость", False)

    def _set_language(self, language: str):
        """Установка языка ассистента."""
        try:
            if language in ['ru', 'en', 'de', 'fr', 'es']:
                self.settings['language'] = language
                self.tts_engine.speak(f"Язык установлен: {language}")
                self.command_executed.emit(f"установи язык {language}", True)
            else:
                self.tts_engine.speak("Этот язык не поддерживается")
                self.command_executed.emit(f"установи язык {language}", False)
        except Exception as e:
            self.logger.error(f"Ошибка установки языка: {e}")
            self.tts_engine.speak("Не удалось установить язык")
            self.command_executed.emit(f"установи язык {language}", False)

    def _set_theme(self, theme: str):
        """Установка темы оформления."""
        try:
            if theme in ['light', 'dark', 'auto']:
                self.settings['theme'] = theme
                # Применение темы к GUI
                if hasattr(self, 'gui') and self.gui:
                    self.gui.apply_theme(theme)
                self.tts_engine.speak(f"Тема установлена: {theme}")
                self.command_executed.emit(f"установи тему {theme}", True)
            else:
                self.tts_engine.speak("Эта тема не поддерживается")
                self.command_executed.emit(f"установи тему {theme}", False)
        except Exception as e:
            self.logger.error(f"Ошибка установки темы: {e}")
            self.tts_engine.speak("Не удалось установить тему")
            self.command_executed.emit(f"установи тему {theme}", False)

    def _restart_assistant(self):
        """Перезапуск ассистента."""
        try:
            self.tts_engine.speak("Перезапускаюсь")
            self.command_executed.emit("перезапустись", True)
            # Здесь должен быть код для перезапуска приложения
            # Временная заглушка - просто выходим
            self.shutdown()
            # В реальном приложении здесь был бы перезапуск
        except Exception as e:
            self.logger.error(f"Ошибка перезапуска ассистента: {e}")
            self.tts_engine.speak("Не удалось перезапуститься")
            self.command_executed.emit("перезапустись", False)

    def _shutdown_assistant(self):
        """Выключение ассистента."""
        try:
            self.tts_engine.speak("Выключаюсь")
            self.command_executed.emit("выключись", True)
            self.shutdown()
        except Exception as e:
            self.logger.error(f"Ошибка выключения ассистента: {e}")
            self.tts_engine.speak("Не удалось выключиться")
            self.command_executed.emit("выключись", False)

    # 3. Творческие команды (продолжение)
    def _generate_text(self, prompt: str, length: int):
        """Генерация текста."""
        try:
            # Используем ML движок для генерации текста
            text = self.inference_engine.generate_text(prompt, length)
            self.automation_manager.insert_text(text)
            self.tts_engine.speak("Текст сгенерирован и вставлен")
            self.command_executed.emit(f"сгенерируй текст {prompt}", True)
        except Exception as e:
            self.logger.error(f"Ошибка генерации текста: {e}")
            self.tts_engine.speak("Не удалось сгенерировать текст")
            self.command_executed.emit(f"сгенерируй текст {prompt}", False)

    def _generate_image(self, description: str):
        """Генерация изображения."""
        try:
            # Используем ML движок для генерации изображения
            image_path = self.inference_engine.generate_image(description)
            self.tts_engine.speak("Изображение сгенерировано")
            # Открываем изображение
            os.startfile(image_path)
            self.command_executed.emit(f"сгенерируй изображение {description}", True)
        except Exception as e:
            self.logger.error(f"Ошибка генерации изображения: {e}")
            self.tts_engine.speak("Не удалось сгенерировать изображение")
            self.command_executed.emit(f"сгенерируй изображение {description}", False)

    def _generate_music(self, genre: str, duration: int):
        """Генерация музыки."""
        try:
            # Используем ML движок для генерации музыки
            music_path = self.inference_engine.generate_music(genre, duration)
            self.tts_engine.speak("Музыка сгенерирована")
            # Воспроизводим музыку
            os.startfile(music_path)
            self.command_executed.emit(f"сгенерируй музыку {genre}", True)
        except Exception as e:
            self.logger.error(f"Ошибка генерации музыки: {e}")
            self.tts_engine.speak("Не удалось сгенерировать музыку")
            self.command_executed.emit(f"сгенерируй музыку {genre}", False)

    # 4. Коммуникационные команды (продолжение)
    def _make_call(self, recipient: str):
        """Совершение звонка."""
        try:
            # Здесь должна быть интеграция с VoIP сервисом или телефоном
            # Временная заглушка
            self.tts_engine.speak(f"Звоню {recipient}")
            self.command_executed.emit(f"позвони {recipient}", True)
        except Exception as e:
            self.logger.error(f"Ошибка совершения звонка: {e}")
            self.tts_engine.speak("Не удалось совершить звонок")
            self.command_executed.emit(f"позвони {recipient}", False)

    def _read_messages(self, count: int):
        """Чтение сообщений."""
        try:
            # Здесь должна быть интеграция с мессенджерами или email
            # Временная заглушка
            messages = "У вас 5 новых сообщений. Первое: Привет, как дела?"
            self.tts_engine.speak(messages)
            self.command_executed.emit("прочитай сообщения", True)
        except Exception as e:
            self.logger.error(f"Ошибка чтения сообщений: {e}")
            self.tts_engine.speak("Не удалось прочитать сообщения")
            self.command_executed.emit("прочитай сообщения", False)

    def _create_event(self, title: str, event_datetime):
        """Создание события."""
        try:
            # Здесь должна быть интеграция с календарем
            # Временная заглушка
            self.tts_engine.speak(f"Событие {title} создано на {event_datetime}")
            self.command_executed.emit(f"создай событие {title}", True)
        except Exception as e:
            self.logger.error(f"Ошибка создания события: {e}")
            self.tts_engine.speak("Не удалось создать событие")
            self.command_executed.emit(f"создай событие {title}", False)

    def _cancel_event(self, title: str):
        """Отмена события."""
        try:
            # Здесь должна быть интеграция с календарем
            # Временная заглушка
            self.tts_engine.speak(f"Событие {title} отменено")
            self.command_executed.emit(f"отмени событие {title}", True)
        except Exception as e:
            self.logger.error(f"Ошибка отмены события: {e}")
            self.tts_engine.speak("Не удалось отменить событие")
            self.command_executed.emit(f"отмени событие {title}", False)

    # 5. Образовательные команды (продолжение)
    def _teach_skill(self, skill: str, duration: int):
        """Обучение навыку."""
        try:
            # Используем ML движок или базу знаний для обучения
            lesson = self.inference_engine.teach_skill(skill, duration)
            self.tts_engine.speak(lesson)
            self.command_executed.emit(f"научи {skill}", True)
        except Exception as e:
            self.logger.error(f"Ошибка обучения навыку: {e}")
            self.tts_engine.speak("Не удалось обучить этому навыку")
            self.command_executed.emit(f"научи {skill}", False)

    def _quiz(self, topic: str, difficulty: str):
        """Проведение викторины."""
        try:
            # Используем ML движок или базу знаний для викторины
            quiz_question = self.inference_engine.generate_quiz(topic, difficulty)
            self.tts_engine.speak(quiz_question)
            self.command_executed.emit(f"викторина {topic}", True)
        except Exception as e:
            self.logger.error(f"Ошибка проведения викторины: {e}")
            self.tts_engine.speak("Не удалось провести викторину")
            self.command_executed.emit(f"викторина {topic}", False)

    # 6. Развлекательные команды (продолжение)
    def _play_game(self, game: str):
        """Запуск игры."""
        try:
            # Сопоставление названий игр с путями
            game_map = {
                'шахматы': 'chess.exe',
                'шашки': 'checkers.exe',
                'солитер': 'solitaire.exe',
                'пасьянс': 'solitaire.exe'
            }

            game_path = game_map.get(game.lower(), game)
            subprocess.Popen(game_path, shell=True)
            self.tts_engine.speak(f"Запускаю {game}")
            self.command_executed.emit(f"играй в {game}", True)
        except Exception as e:
            self.logger.error(f"Ошибка запуска игры: {e}")
            self.tts_engine.speak(f"Не удалось запустить {game}")
            self.command_executed.emit(f"играй в {game}", False)

    def _play_music(self, query: str):
        """Воспроизведение музыки."""
        try:
            # Здесь должна быть интеграция с музыкальным сервисом
            # Временная заглушка
            self.tts_engine.speak(f"Включаю музыку: {query}")
            # Запускаем музыкальный проигрыватель
            os.system("start wmplayer")
            self.command_executed.emit(f"включи музыку {query}", True)
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения музыки: {e}")
            self.tts_engine.speak("Не удалось воспроизвести музыку")
            self.command_executed.emit(f"включи музыку {query}", False)

    def _play_radio(self, station: str):
        """Воспроизведение радио."""
        try:
            # Здесь должна быть интеграция с радиостанциями
            # Временная заглушка
            self.tts_engine.speak(f"Включаю радиостанцию: {station}")
            # Запускаем радио проигрыватель
            os.system("start wmplayer")
            self.command_executed.emit(f"включи радио {station}", True)
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения радио: {e}")
            self.tts_engine.speak("Не удалось воспроизвести радио")
            self.command_executed.emit(f"включи радио {station}", False)

    def _watch_movie(self, title: str):
        """Просмотр фильма."""
        try:
            # Здесь должна быть интеграция с видео сервисом
            # Временная заглушка
            self.tts_engine.speak(f"Включаю фильм: {title}")
            # Запускаем видео проигрыватель
            os.system("start wmplayer")
            self.command_executed.emit(f"включи фильм {title}", True)
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения фильма: {e}")
            self.tts_engine.speak("Не удалось воспроизвести фильм")
            self.command_executed.emit(f"включи фильм {title}", False)

    # 7. Навигационные команды (продолжение)
    def _find_location(self, query: str, location: str):
        """Поиск местоположения."""
        try:
            # Здесь должен быть API запрос к картографическому сервису
            # Временная заглушка
            result = f"Найдено местоположение: {query} в {location}"
            self.tts_engine.speak(result)
            self.command_executed.emit(f"найди {query} в {location}", True)
        except Exception as e:
            self.logger.error(f"Ошибка поиска местоположения: {e}")
            self.tts_engine.speak("Не удалось найти местоположение")
            self.command_executed.emit(f"найди {query} в {location}", False)

    def _get_directions(self, from_location: str, to_location: str, mode: str):
        """Получение маршрута."""
        try:
            # Здесь должен быть API запрос к картографическому сервису
            # Временная заглушка
            directions = f"Маршрут от {from_location} до {to_location}: 5 км, 15 минут"
            self.tts_engine.speak(directions)
            self.command_executed.emit(f"маршрут от {from_location} до {to_location}", True)
        except Exception as e:
            self.logger.error(f"Ошибка получения маршрута: {e}")
            self.tts_engine.speak("Не удалось получить маршрут")
            self.command_executed.emit(f"маршрут от {from_location} до {to_location}", False)

    def _get_traffic_info(self, route: str):
        """Получение информации о трафике."""
        try:
            # Здесь должен быть API запрос к сервису трафика
            # Временная заглушка
            traffic = f"Информация о трафике на маршруте {route}: пробки 3 балла, время в пути 20 минут"
            self.tts_engine.speak(traffic)
            self.command_executed.emit(f"трафик {route}", True)
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о трафике: {e}")
            self.tts_engine.speak("Не удалось получить информацию о трафике")
            self.command_executed.emit(f"трафик {route}", False)

    # 8. Команды для работы с файлами (продолжение)
    def _create_file(self, name: str, content: str):
        """Создание файла."""
        try:
            # Создаем файл с указанным именем и содержимым
            with open(name, 'w', encoding='utf-8') as f:
                f.write(content)
            self.tts_engine.speak(f"Файл {name} создан")
            self.command_executed.emit(f"создай файл {name}", True)
        except Exception as e:
            self.logger.error(f"Ошибка создания файла: {e}")
            self.tts_engine.speak("Не удалось создать файл")
            self.command_executed.emit(f"создай файл {name}", False)

    def _read_file(self, path: str):
        """Чтение файла."""
        try:
            # Читаем содержимое файла
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.tts_engine.speak(f"Содержимое файла {path}: {content[:100]}...")
            self.command_executed.emit(f"прочитай файл {path}", True)
        except Exception as e:
            self.logger.error(f"Ошибка чтения файла: {e}")
            self.tts_engine.speak("Не удалось прочитать файл")
            self.command_executed.emit(f"прочитай файл {path}", False)

    def _write_file(self, path: str, content: str):
        """Запись в файл."""
        try:
            # Записываем содержимое в файл
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.tts_engine.speak(f"Файл {path} обновлен")
            self.command_executed.emit(f"запиши в файл {path}", True)
        except Exception as e:
            self.logger.error(f"Ошибка записи в файл: {e}")
            self.tts_engine.speak("Не удалось записать в файл")
            self.command_executed.emit(f"запиши в файл {path}", False)

    def _delete_file(self, path: str):
        """Удаление файла."""
        try:
            # Удаляем файл
            os.remove(path)
            self.tts_engine.speak(f"Файл {path} удален")
            self.command_executed.emit(f"удали файл {path}", True)
        except Exception as e:
            self.logger.error(f"Ошибка удаления файла: {e}")
            self.tts_engine.speak("Не удалось удалить файл")
            self.command_executed.emit(f"удали файл {path}", False)

    def _organize_files(self, directory: str, method: str):
        """Организация файлов."""
        try:
            # Организуем файлы в указанной директории
            if method == 'type':
                # Группируем по типу файла
                for filename in os.listdir(directory):
                    if os.path.isfile(os.path.join(directory, filename)):
                        file_ext = filename.split('.')[-1]
                        ext_dir = os.path.join(directory, file_ext)
                        os.makedirs(ext_dir, exist_ok=True)
                        os.rename(
                            os.path.join(directory, filename),
                            os.path.join(ext_dir, filename)
                        )
            self.tts_engine.speak(f"Файлы в {directory} организованы по {method}")
            self.command_executed.emit(f"организуй файлы в {directory}", True)
        except Exception as e:
            self.logger.error(f"Ошибка организации файлов: {e}")
            self.tts_engine.speak("Не удалось организовать файлы")
            self.command_executed.emit(f"организуй файлы в {directory}", False)

    # 9. Команды для работы с приложениями (продолжение)
    def _install_application(self, name: str):
        """Установка приложения."""
        try:
            # Здесь должна быть интеграция с магазином приложений или установщиком
            # Временная заглушка
            self.tts_engine.speak(f"Устанавливаю приложение {name}")
            self.command_executed.emit(f"установи приложение {name}", True)
        except Exception as e:
            self.logger.error(f"Ошибка установки приложения: {e}")
            self.tts_engine.speak("Не удалось установить приложение")
            self.command_executed.emit(f"установи приложение {name}", False)

    def _uninstall_application(self, name: str):
        """Удаление приложения."""
        try:
            # Здесь должна быть интеграция с менеджером приложений
            # Временная заглушка
            self.tts_engine.speak(f"Удаляю приложение {name}")
            self.command_executed.emit(f"удали приложение {name}", True)
        except Exception as e:
            self.logger.error(f"Ошибка удаления приложения: {e}")
            self.tts_engine.speak("Не удалось удалить приложение")
            self.command_executed.emit(f"удали приложение {name}", False)

    def _search_in_application(self, application: str, query: str):
        """Поиск в приложении."""
        try:
            # Здесь должна быть интеграция с конкретным приложением
            # Временная заглушка
            self.tts_engine.speak(f"Ищу {query} в {application}")
            self.command_executed.emit(f"найди {query} в {application}", True)
        except Exception as e:
            self.logger.error(f"Ошибка поиска в приложении: {e}")
            self.tts_engine.speak("Не удалось выполнить поиск в приложении")
            self.command_executed.emit(f"найди {query} в {application}", False)

    # 10. Команды для самоанализа и рефлексии (продолжение)
    def _get_usage_stats(self, period: str):
        """Получение статистики использования."""
        try:
            # Анализируем историю команд за указанный период
            now = datetime.now()
            if period == 'day':
                start_time = now - timedelta(days=1)
            elif period == 'week':
                start_time = now - timedelta(weeks=1)
            elif period == 'month':
                start_time = now - timedelta(days=30)
            else:
                start_time = now - timedelta(days=1)

            recent_commands = [
                cmd for cmd in self.command_history
                if cmd['timestamp'] > start_time
            ]

            stats = f"За последний {period} выполнено {len(recent_commands)} команд"
            self.tts_engine.speak(stats)
            self.command_executed.emit(f"статистика за {period}", True)
        except Exception as e:
            self.logger.error(f"Ошибка получения статистики: {e}")
            self.tts_engine.speak("Не удалось получить статистику")
            self.command_executed.emit(f"статистика за {period}", False)

    def _get_behavior_report(self):
        """Получение отчета о поведении."""
        try:
            # Анализируем поведение ассистента
            total_commands = len(self.command_history)
            successful_commands = sum(1 for cmd in self.command_history
                                      if 'success' in cmd and cmd['success'])
            success_rate = (successful_commands / total_commands * 100) if total_commands > 0 else 0

            report = f"Всего выполнено команд: {total_commands}. Успешных: {success_rate:.1f}%"
            self.tts_engine.speak(report)
            self.command_executed.emit("отчет о поведении", True)
        except Exception as e:
            self.logger.error(f"Ошибка получения отчета о поведении: {e}")
            self.tts_engine.speak("Не удалось получить отчет о поведении")
            self.command_executed.emit("отчет о поведении", False)

    def _provide_feedback(self, feedback: str):
        """Предоставление обратной связи."""
        try:
            # Сохраняем обратную связь для улучшения ассистента
            feedback_file = "feedback.txt"
            with open(feedback_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now()}: {feedback}\n")

            self.tts_engine.speak("Спасибо за обратную связь!")
            self.command_executed.emit("обратная связь", True)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения обратной связи: {e}")
            self.tts_engine.speak("Не удалось сохранить обратную связь")
            self.command_executed.emit("обратная связь", False)

    # 11. Команды для выполнения сложных задач (продолжение)
    def _plan_event(self, event_type: str, event_date, guests: int):
        """Планирование мероприятия."""
        try:
            # Используем планировщик задач для организации мероприятия
            event_id = self.task_scheduler.plan_event(
                event_type, event_date, guests
            )
            self.tts_engine.speak(f"Мероприятие {event_type} запланировано на {event_date}")
            self.command_executed.emit(f"запланируй мероприятие {event_type}", True)
        except Exception as e:
            self.logger.error(f"Ошибка планирования мероприятия: {e}")
            self.tts_engine.speak("Не удалось запланировать мероприятие")
            self.command_executed.emit(f"запланируй мероприятие {event_type}", False)

    def _manage_project(self, project: str, action: str, deadline):
        """Управление проектом."""
        try:
            # Используем планировщик задач для управления проектом
            if action == 'start':
                self.task_scheduler.start_project(project, deadline)
                self.tts_engine.speak(f"Проект {project} запущен")
            elif action == 'pause':
                self.task_scheduler.pause_project(project)
                self.tts_engine.speak(f"Проект {project} приостановлен")
            elif action == 'resume':
                self.task_scheduler.resume_project(project)
                self.tts_engine.speak(f"Проект {project} возобновлен")
            elif action == 'complete':
                self.task_scheduler.complete_project(project)
                self.tts_engine.speak(f"Проект {project} завершен")

            self.command_executed.emit(f"управляй проектом {project}", True)
        except Exception as e:
            self.logger.error(f"Ошибка управления проектом: {e}")
            self.tts_engine.speak("Не удалось управлять проектом")
            self.command_executed.emit(f"управляй проектом {project}", False)

    def _solve_problem(self, problem: str):
        """Решение проблемы."""
        try:
            # Используем ML движок для решения проблемы
            solution = self.inference_engine.solve_problem(problem)
            self.tts_engine.speak(f"Решение проблемы: {solution}")
            self.command_executed.emit(f"реши проблему {problem}", True)
        except Exception as e:
            self.logger.error(f"Ошибка решения проблемы: {e}")
            self.tts_engine.speak("Не удалось решить проблему")
            self.command_executed.emit(f"реши проблему {problem}", False)

    # 12. Команды, связанные с безопасностью и конфиденциальностью (продолжение)
    def _lock_device(self):
        """Блокировка устройства."""
        try:
            # Блокируем устройство
            os.system("rundll32.exe user32.dll,LockWorkStation")
            self.tts_engine.speak("Устройство заблокировано")
            self.command_executed.emit("заблокируй устройство", True)
        except Exception as e:
            self.logger.error(f"Ошибка блокировки устройства: {e}")
            self.tts_engine.speak("Не удалось заблокировать устройство")
            self.command_executed.emit("заблокируй устройство", False)

    def _unlock_device(self):
        """Разблокировка устройства."""
        try:
            # Здесь должна быть интеграция с системой аутентификации
            # Временная заглушка
            self.tts_engine.speak("Устройство разблокировано")
            self.command_executed.emit("разблокируй устройство", True)
        except Exception as e:
            self.logger.error(f"Ошибка разблокировки устройства: {e}")
            self.tts_engine.speak("Не удалось разблокировать устройство")
            self.command_executed.emit("разблокируй устройство", False)

    def _encrypt_file(self, path: str):
        """Шифрование файла."""
        try:
            # Шифруем файл
            # Здесь должен быть код для шифрования
            # Временная заглушка
            self.tts_engine.speak(f"Файл {path} зашифрован")
            self.command_executed.emit(f"зашифруй файл {path}", True)
        except Exception as e:
            self.logger.error(f"Ошибка шифрования файла: {e}")
            self.tts_engine.speak("Не удалось зашифровать файл")
            self.command_executed.emit(f"зашифруй файл {path}", False)

    def _decrypt_file(self, path: str):
        """Дешифрование файла."""
        try:
            # Дешифруем файл
            # Здесь должен быть код для дешифрования
            # Временная заглушка
            self.tts_engine.speak(f"Файл {path} расшифрован")
            self.command_executed.emit(f"расшифруй файл {path}", True)
        except Exception as e:
            self.logger.error(f"Ошибка дешифрования файла: {e}")
            self.tts_engine.speak("Не удалось расшифровать файл")
            self.command_executed.emit(f"расшифруй файл {path}", False)

    def _change_password(self, service: str, new_password: str):
        """Изменение пароля."""
        try:
            # Изменяем пароль для указанного сервиса
            # Здесь должна быть интеграция с менеджером паролей
            # Временная заглушка
            self.tts_engine.speak(f"Пароль для {service} изменен")
            self.command_executed.emit(f"измени пароль для {service}", True)
        except Exception as e:
            self.logger.error(f"Ошибка изменения пароля: {e}")
            self.tts_engine.speak("Не удалось изменить пароль")
            self.command_executed.emit(f"измени пароль для {service}", False)

    # 13. Системные команды ассистента (продолжение)
    def _show_history(self, count: int):
        """Показать историю команд."""
        try:
            # Показываем последние N команд
            recent_commands = self.command_history[-count:]
            history_text = "Последние команды: "
            for cmd in recent_commands:
                history_text += f"{cmd['command']}, "

            self.tts_engine.speak(history_text)
            self.command_executed.emit("покажи историю", True)
        except Exception as e:
            self.logger.error(f"Ошибка показа истории: {e}")
            self.tts_engine.speak("Не удалось показать историю")
            self.command_executed.emit("покажи историю", False)

    def run(self) -> int:
        """Запуск основного цикла приложения."""
        try:
            self.logger.info("Запуск приложения Лиза")

            # Инициализация приложения
            if not self.initialize():
                return 1

            # Создание GUI
            app = QApplication([])
            self.gui = MainWindow(self)
            self.gui.show()

            # Запуск компонентов
            self.voice_engine.start_listening()
            self.is_running = True

            self.logger.info("Приложение успешно запущено")
            self.status_changed.emit("Готов к работе")
            self.tts_engine.speak("Лиза готова к работе")

            # Запуск основного цикла
            return app.exec()

        except Exception as e:
            self.logger.critical(f"Критическая ошибка при запуске приложения: {e}")
            return 1

    def shutdown(self):
        """Корректное завершение работы приложения."""
        self.logger.info("Завершение работы приложения...")
        self.is_running = False

        if self.voice_engine:
            self.voice_engine.stop_listening()

        if self.task_scheduler:
            self.task_scheduler.shutdown()

        # Сохраняем кэш путей приложений
        self._save_app_paths_cache()

        self.logger.info("Приложение завершило работу")