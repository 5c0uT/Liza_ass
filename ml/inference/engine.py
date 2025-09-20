"""
Движок инференса для AI-ассистента Лиза.
"""

import logging
import torch
import numpy as np
from typing import Dict, Any, List, Optional
from pathlib import Path

from ml.models.fusion_net import FusionNet
from ml.models.action_predictor import ActionPredictor
from ml.models.code_generator import CodeGenerator
from ml.inference.optimizations import optimize_model, quantize_model, optimize_for_device


class InferenceEngine:
    """Движок для выполнения инференса моделей машинного обучения."""

    def __init__(self, device: str = None):
        self.logger = logging.getLogger(__name__)

        # Автоматическое определение устройства, если не указано
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.logger.info(f"Инициализация InferenceEngine на устройстве: {self.device}")

        # Загруженные модели
        self.models = {}

        # Кэш для хранения информации о моделях
        self.model_info_cache = {}

    def load_model(self, model_name: str, model_path: Optional[Path] = None,
                  model_class: Any = None, model_config: Dict[str, Any] = None,
                  optimization_level: str = "default") -> bool:
        """
        Загрузка модели для инференса.

        Args:
            model_name: Имя модели для регистрации
            model_path: Путь к файлу модели
            model_class: Класс модели (если нужно создать новую)
            model_config: Конфигурация модели
            optimization_level: Уровень оптимизации

        Returns:
            True если модель успешно загружена
        """
        try:
            if model_config is None:
                model_config = {}

            if model_path and model_path.exists():
                # Загрузка сохраненной модели
                self.logger.info(f"Загрузка модели из файла: {model_path}")
                model_data = torch.load(model_path, map_location=self.device)

                if model_class:
                    # Создание экземпляра и загрузка весов
                    model = model_class(**model_config)
                    if 'model_state_dict' in model_data:
                        model.load_state_dict(model_data['model_state_dict'])
                    else:
                        model.load_state_dict(model_data)
                else:
                    # Загрузка всей модели
                    model = model_data

            elif model_class:
                # Создание новой модели
                self.logger.info(f"Создание новой модели: {model_name}")
                model = model_class(**model_config)
            else:
                self.logger.error("Не указан model_class для создания модели")
                return False

            # Оптимизация модели
            model = optimize_model(model, optimization_level)

            # Оптимизация для конкретного устройства
            model = optimize_for_device(model, self.device)

            # Перемещение на device и установка в eval mode
            model.to(self.device)
            model.eval()

            self.models[model_name] = model
            self.logger.info(f"Модель '{model_name}' успешно загружена и оптимизирована")

            # Сохранение информации о модели
            self.model_info_cache[model_name] = self._get_model_info(model)

            return True

        except Exception as e:
            self.logger.error(f"Ошибка загрузки модели '{model_name}': {e}")
            return False

    def _get_model_info(self, model: torch.nn.Module) -> Dict[str, Any]:
        """Получение подробной информации о модели."""
        try:
            # Подсчет параметров
            total_params = sum(p.numel() for p in model.parameters())
            trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

            # Размер модели в памяти
            param_size = 0
            for param in model.parameters():
                param_size += param.nelement() * param.element_size()
            for buffer in model.buffers():
                param_size += buffer.nelement() * buffer.element_size()

            size_mb = param_size / 1024**2

            return {
                'total_parameters': total_params,
                'trainable_parameters': trainable_params,
                'size_mb': size_mb,
                'device': str(next(model.parameters()).device)
            }
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о модели: {e}")
            return {}

    def unload_model(self, model_name: str) -> bool:
        """Выгрузка модели."""
        if model_name in self.models:
            # Освобождение памяти
            del self.models[model_name]

            # Очистка кэша
            if model_name in self.model_info_cache:
                del self.model_info_cache[model_name]

            # Очистка кэша CUDA если используется
            if self.device == "cuda":
                torch.cuda.empty_cache()

            self.logger.info(f"Модель '{model_name}' выгружена")
            return True
        return False

    def unload_all_models(self):
        """Выгрузка всех моделей."""
        for model_name in list(self.models.keys()):
            self.unload_model(model_name)
        self.logger.info("Все модели выгружены")

    def process_command(self, command: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Обработка пользовательской команды с использованием моделей.

        Args:
            command: Текст команды
            context: Контекст выполнения

        Returns:
            Результат обработки команды
        """
        if context is None:
            context = {}

        try:
            # Очистка и нормализация команды
            cleaned_command = self._preprocess_command(command)

            if not cleaned_command:
                return {'action': 'error', 'message': 'Пустая команда'}

            # Извлечение намерения (intent)
            intent, confidence = self._extract_intent(cleaned_command)

            self.logger.info(f"Распознано намерение: {intent} (уверенность: {confidence:.2f})")

            # Обработка в зависимости от намерения
            if intent == 'code_generation':
                return self._handle_code_generation(cleaned_command, context, confidence)
            elif intent == 'action_prediction':
                return self._handle_action_prediction(cleaned_command, context, confidence)
            elif intent == 'system_control':
                return self._handle_system_control(cleaned_command, context, confidence)
            else:
                return {'action': 'unknown', 'confidence': confidence}

        except Exception as e:
            self.logger.error(f"Ошибка обработки команды: {e}")
            return {'action': 'error', 'message': str(e)}

    def _preprocess_command(self, command: str) -> str:
        """Предварительная обработка команды."""
        # Удаление лишних пробелов и приведение к нижнему регистру
        cleaned = ' '.join(command.strip().split()).lower()

        # Удаление стоп-слов (можно расширить список)
        stop_words = {'пожалуйста', 'можешь', 'ли', 'мне', 'сейчас'}
        words = cleaned.split()
        filtered_words = [word for word in words if word not in stop_words]

        return ' '.join(filtered_words)

    def _extract_intent(self, command: str) -> tuple:
        """Извлечение намерения из команды с оценкой уверенности."""
        # Более сложная логика извлечения намерения
        command_lower = command.lower()

        intent_patterns = {
            'code_generation': [
                'напиши', 'создай', 'код', 'функци', 'класс', 'программу',
                'скрипт', 'алгоритм', 'реализуй', 'написать', 'создать'
            ],
            'action_prediction': [
                'запусти', 'открой', 'выполни', 'сделай', 'включи',
                'закрой', 'останови', 'перезагрузи', 'управляй'
            ],
            'system_control': [
                'систем', 'памят', 'процесс', 'монитор', 'ресурс',
                'диск', 'процессор', 'cpu', 'memory', 'загрузка'
            ]
        }

        best_intent = 'unknown'
        max_confidence = 0.0

        for intent, patterns in intent_patterns.items():
            matches = sum(1 for pattern in patterns if pattern in command_lower)
            confidence = matches / len(patterns) if patterns else 0

            if confidence > max_confidence:
                max_confidence = confidence
                best_intent = intent

        # Минимальная уверенность для принятия решения
        if max_confidence < 0.2:
            best_intent = 'unknown'
            max_confidence = 0.0

        return best_intent, max_confidence

    def _handle_code_generation(self, command: str, context: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Обработка запроса генерации кода."""
        if 'code_generator' not in self.models:
            self.logger.warning("Модель генерации кода не загружена")
            return {'action': 'error', 'message': 'Модель генерации кода не доступна'}

        try:
            # Определение языка программирования из контекста или команды
            language = context.get('language', 'python')
            lang_keywords = {
                'python': ['python', 'питон', 'пайтон'],
                'javascript': ['javascript', 'js', 'джаваскрипт'],
                'java': ['java', 'джава'],
                'html': ['html', 'хтмл'],
                'css': ['css', 'цсс'],
                'sql': ['sql', ' sequel', 'эскьюэль']
            }

            for lang, keywords in lang_keywords.items():
                if any(keyword in command.lower() for keyword in keywords):
                    language = lang
                    break

            # Генерация кода
            generated_code = self.models['code_generator'].generate(
                prompt=command,
                language=language,
                max_length=context.get('max_length', 200)
            )

            return {
                'action': 'code_generation',
                'language': language,
                'code': generated_code,
                'confidence': confidence
            }

        except Exception as e:
            self.logger.error(f"Ошибка генерации кода: {e}")
            return {'action': 'error', 'message': str(e), 'confidence': confidence}

    def _handle_action_prediction(self, command: str, context: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Обработка запроса предсказания действия."""
        if 'action_predictor' not in self.models:
            self.logger.warning("Модель предсказания действий не загружена")
            return {'action': 'error', 'message': 'Модель предсказания действий не доступна'}

        try:
            # Создание фич из команды (упрощенная версия)
            # В реальной реализации здесь должен быть полноценный препроцессинг
            features = self._extract_features_from_command(command, context)

            if features is None:
                return {'action': 'error', 'message': 'Не удалось извлечь фичи из команды', 'confidence': confidence}

            # Предсказание действия
            prediction = self.models['action_predictor'].predict(features, top_k=3)

            return {
                'action': 'action_prediction',
                'predictions': prediction['indices'].tolist(),
                'probabilities': prediction['probabilities'].tolist(),
                'confidence': float(np.max(prediction['probabilities'])) * confidence
            }

        except Exception as e:
            self.logger.error(f"Ошибка предсказания действия: {e}")
            return {'action': 'error', 'message': str(e), 'confidence': confidence}

    def _extract_features_from_command(self, command: str, context: Dict[str, Any]) -> Optional[torch.Tensor]:
        """Извлечение признаков из команды для модели предсказания действий."""
        try:
            # Упрощенная реализация - в реальном приложении нужно использовать
            # embedding модель для преобразования текста в вектор
            from sentence_transformers import SentenceTransformer

            # Используем небольшую модель для эмбеддингов
            embedding_model = SentenceTransformer('paraphrase-albert-small-v2')
            embedding = embedding_model.encode([command])

            # Преобразование в тензор и добавление временных измерений
            features = torch.tensor(embedding, dtype=torch.float32)
            features = features.unsqueeze(0)  # Добавляем batch dimension
            features = features.unsqueeze(1)  # Добавляем sequence dimension

            return features.to(self.device)

        except Exception as e:
            self.logger.error(f"Ошибка извлечения признаков: {e}")
            return None

    def _handle_system_control(self, command: str, context: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Обработка запроса управления системой."""
        # Анализ команды для определения конкретного действия
        command_lower = command.lower()

        system_actions = {
            'монитор': 'system_monitor',
            'память': 'memory_info',
            'процессор': 'cpu_info',
            'диск': 'disk_info',
            'процессы': 'process_list',
            'ресурсы': 'resource_usage'
        }

        action = 'system_info'  # Действие по умолчанию

        for keyword, sys_action in system_actions.items():
            if keyword in command_lower:
                action = sys_action
                break

        return {
            'action': 'system_control',
            'command': command,
            'system_action': action,
            'confidence': confidence
        }

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Получение информации о модели."""
        if model_name in self.model_info_cache:
            return self.model_info_cache[model_name]

        if model_name not in self.models:
            return None

        model = self.models[model_name]
        info = self._get_model_info(model)

        # Добавление специфичной информации для разных типов моделей
        if hasattr(model, 'input_dim'):
            info['input_dim'] = model.input_dim
        if hasattr(model, 'hidden_dim'):
            info['hidden_dim'] = model.hidden_dim
        if hasattr(model, 'num_actions'):
            info['num_actions'] = model.num_actions

        # Сохранение в кэш
        self.model_info_cache[model_name] = info

        return info

    def get_loaded_models(self) -> List[str]:
        """Получение списка загруженных моделей."""
        return list(self.models.keys())

    def get_available_devices(self) -> List[str]:
        """Получение списка доступных устройств."""
        devices = ['cpu']

        if torch.cuda.is_available():
            devices.append('cuda')

        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            devices.append('mps')

        return devices

    def switch_device(self, new_device: str) -> bool:
        """
        Переключение на другое устройство.

        Args:
            new_device: Новое устройство (cpu, cuda, mps)

        Returns:
            True если переключение успешно
        """
        if new_device not in self.get_available_devices():
            self.logger.error(f"Устройство {new_device} не доступно")
            return False

        if new_device == self.device:
            self.logger.warning(f"Уже используется устройство {new_device}")
            return True

        try:
            # Выгружаем все модели
            self.unload_all_models()

            # Меняем устройство
            self.device = new_device
            self.logger.info(f"Переключено на устройство: {new_device}")

            return True

        except Exception as e:
            self.logger.error(f"Ошибка переключения устройства: {e}")
            return False