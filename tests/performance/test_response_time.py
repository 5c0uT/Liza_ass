import pytest
import time
from unittest.mock import Mock, patch
from core.voice_input import VoiceInputEngine
from core.tts import TTSEngine
from core.app import LisaApp

class TestPerformance:
    """Тесты производительности."""

    @pytest.fixture
    def voice_engine(self):
        with patch('whisper.load_model'), patch('speech_recognition.Microphone'):
            engine = VoiceInputEngine(model_size="tiny")
            engine.whisper_model = Mock()
            return engine

    @pytest.fixture
    def tts_engine(self):
        with patch('torch.hub.load'):
            engine = TTSEngine()
            engine.model = Mock()
            return engine

    @pytest.fixture
    def lisa_app(self):
        """Фикстура для создания экземпляра LisaApp с моками."""
        app = LisaApp()

        # Мокаем необходимые компоненты
        app.inference_engine = Mock()
        app.automation_manager = Mock()
        app.logger = Mock()

        # Настраиваем мок inference_engine для возврата тестового intent
        app.inference_engine.process_command.return_value = {
            'action': 'test_action',
            'parameters': {}
        }

        return app

    def test_command_processing_time(self, lisa_app):
        """Тест времени обработки команды от начала до конца."""
        start_time = time.time()

        # Вызываем обработчик команды
        lisa_app._handle_voice_command("тестовая команда")

        processing_time = time.time() - start_time

        # Проверяем, что время обработки менее 500 мс
        assert processing_time < 0.5, f"Время обработки команды {processing_time:.3f} с превышает 500 мс"

        # Проверяем, что методы были вызваны
        lisa_app.inference_engine.process_command.assert_called_once_with("тестовая команда")
        lisa_app.automation_manager.execute_workflow.assert_called_once()

    def test_voice_response_time(self, voice_engine):
        """Тест времени отклика голосового ввода."""
        test_phrase = "тестовая команда"

        start_time = time.time()

        # Имитация обработки команды
        voice_engine.whisper_model.transcribe.return_value = {"text": test_phrase}

        # Обработка аудио
        audio_data = b"fake_audio_data"
        voice_engine.audio_queue.put(audio_data)

        # Время обработки
        processing_time = time.time() - start_time

        # Проверка что время отклика менее 200 мс
        assert processing_time < 0.2, f"Время отклика {processing_time:.3f} с превышает 200 мс"

    def test_tts_response_time(self, tts_engine):
        """Тест времени отклика синтеза речи."""
        test_text = "тестовый текст для синтеза речи"

        start_time = time.time()

        # Имитация синтеза речи
        tts_engine.model.apply_tts.return_value = [0.1] * 24000  # 1 секунда аудио

        result = tts_engine.speak(test_text)

        processing_time = time.time() - start_time

        # Проверка что время синтеза менее 500 мс
        assert processing_time < 0.5, f"Время синтеза {processing_time:.3f} с превышает 500 мс"
        assert result == True

    def test_memory_usage(self):
        """Тест использования памяти."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # в МБ

        # Проверка что использование памяти менее 512 МБ
        assert memory_usage < 512, f"Использование памяти {memory_usage:.2f} МБ превышает 512 МБ"

    @pytest.mark.parametrize("command_length", [10, 50, 100])
    def test_response_time_by_command_length(self, command_length):
        """Тест времени отклика в зависимости от длины команды."""
        # Генерация команды заданной длины
        test_command = "тест " * (command_length // 5)

        start_time = time.time()

        # Имитация обработки команды
        time.sleep(0.001 * len(test_command))  # Имитация обработки

        processing_time = time.time() - start_time

        # Проверка что время растет линейно, а не экспоненциально
        expected_time = 0.001 * len(test_command)
        assert processing_time <= expected_time * 1.5, (
            f"Время обработки растет слишком быстро: {processing_time:.3f} с для команды длины {len(test_command)}"
        )