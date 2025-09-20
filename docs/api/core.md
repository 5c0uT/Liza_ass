# API документация: Основное ядро

## Модуль core.app

### Класс LisaApp

Главный класс приложения Лиза.

#### Методы

##### `__init__()`
Инициализация приложения и всех компонентов.

##### `initialize() -> bool`
Инициализация всех компонентов приложения.

Возвращает:
- `True` если инициализация успешна
- `False` если произошла ошибка

##### `run() -> int`
Запуск основного цикла приложения.

Возвращает:
- Код выхода приложения

##### `shutdown()`
Корректное завершение работы приложения.

#### Сигналы

##### `voice_command_received(str)`
Излучается при получении голосовой команды.

##### `status_changed(str)`
Излучается при изменении статуса приложения.

## Модуль core.voice_input

### Класс VoiceInputEngine

Движок голосового ввода с непрерывным прослушиванием.

#### Методы

##### `__init__(model_size: str = "base", energy_threshold: int = 1000, pause_threshold: float = 0.8)`
Инициализация движка голосового ввода.

Параметры:
- `model_size`: Размер модели Whisper
- `energy_threshold`: Порог энергии для активации
- `pause_threshold`: Порог паузы для завершения фразы

##### `start_listening()`
Запуск непрерывного прослушивания.

##### `stop_listening()`
Остановка прослушивания.

#### Сигналы

##### `command_received(str)`
Излучается при распознавании команды.

## Модуль core.tts

### Класс TTSEngine

Движок синтеза речи на основе Silero TTS.

#### Методы

##### `__init__(model_path: Optional[str] = None, device: str = "cpu")`
Инициализация движка синтеза речи.

Параметры:
- `model_path`: Путь к кастомной модели
- `device`: Устройство для выполнения (cpu/cuda)

##### `speak(text: str, speaker: Optional[str] = None) -> bool`
Синтез речи из текста.

Параметры:
- `text`: Текст для синтеза
- `speaker`: Голос для синтеза

Возвращает:
- `True` если синтез успешен
- `False` если произошла ошибка

##### `save_to_file(text: str, filename: str, speaker: Optional[str] = None) -> bool`
Сохранение синтезированной речи в файл.

Параметры:
- `text`: Текст для синтеза
- `filename`: Имя файла для сохранения
- `speaker`: Голос для синтеза

Возвращает:
- `True` если сохранение успешно
- `False` если произошла ошибка

## Модуль core.automation

### Класс AutomationManager

Главный менеджер автоматизации, объединяющий все модули.

#### Методы

##### `__init__()`
Инициализация менеджера автоматизации.

##### `execute_workflow(workflow_id: str) -> bool`
Выполнение workflow по идентификатору.

Параметры:
- `workflow_id`: Идентификатор workflow

Возвращает:
- `True` если выполнение успешно
- `False` если произошла ошибка

#### Компоненты

##### `window_manager: WindowManager`
Менеджер управления окнами.

##### `file_manager: FileManager`
Менеджер управления файлами.

##### `process_manager: ProcessManager`
Менеджер управления процессами.

##### `system_monitor: SystemMonitor`
Монитор системы.

## Примеры использования

### Базовый пример

```python
from core.app import LisaApp

# Создание и запуск приложения
app = LisaApp()
app.initialize()
app.run()
```
# Голосовое управление
```python
from core.voice_input import VoiceInputEngine

# Создание движка голосового ввода
voice_engine = VoiceInputEngine()
voice_engine.command_received.connect(handle_command)
voice_engine.start_listening()

def handle_command(command: str):
    print(f"Получена команда: {command}")
```
# Синтез речи
```python
from core.tts import TTSEngine

# Создание движка синтеза речи
tts_engine = TTSEngine()
tts_engine.speak("Привет, я Лиза, ваш AI ассистент")
```
# Автоматизация
```python
from core.automation import AutomationManager

# Создание менеджера автоматизации
automation = AutomationManager()

# Открытие приложения
automation.window_manager.find_window("Visual Studio Code")
```
# Обработка ошибок
Все методы возвращают значения или излучают сигналы для обработки ошибок. Рекомендуется использовать try-except блоки для критичных операций.

```python
try:
    app.initialize()
except Exception as e:
    print(f"Ошибка инициализации: {e}")
```
# Расширение функциональности
Для добавления новой функциональности создайте новый модуль в соответствующем package и зарегистрируйте его в главном классе приложения.