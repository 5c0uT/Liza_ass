"""
Модульные тесты для голосового ввода.
"""

import pytest
import tempfile
import numpy as np
from unittest.mock import Mock, patch
from core.voice_input import VoiceInputEngine

class TestVoiceInputEngine:
    """Тесты для VoiceInputEngine."""

    @pytest.fixture
    def voice_engine(self):
        """Создание экземпляра VoiceInputEngine для тестов."""
        with patch('whisper.load_model'), patch('speech_recognition.Microphone'):
            engine = VoiceInputEngine(model_size="tiny")
            engine.whisper_model = Mock()
            yield engine

    def test_initialization(self, voice_engine):
        """Тест инициализации движка."""
        assert voice_engine is not None
        assert voice_engine.model_size == "tiny"

    def test_adjust_microphone(self, voice_engine):
        """Тест настройки микрофона."""
        with patch.object(voice_engine.recognizer, 'adjust_for_ambient_noise'):
            # Не должно быть исключений
            voice_engine._adjust_microphone()

    def test_audio_callback(self, voice_engine):
        """Тест обработки аудио callback."""
        mock_audio = Mock()
        mock_audio.get_raw_data.return_value = b'test_audio_data'

        # Вызов callback
        voice_engine._audio_callback(voice_engine.recognizer, mock_audio)

        # Проверка, что данные добавлены в очередь
        assert not voice_engine.audio_queue.empty()

    def test_process_audio_queue(self, voice_engine):
        """Тест обработки аудио очереди."""
        voice_engine.is_listening = True
        voice_engine.whisper_model.transcribe.return_value = {"text": "тестовая команда"}

        # Добавление тестовых данных в очередь
        test_audio = np.random.randint(-32768, 32767, 24000, dtype=np.int16)
        voice_engine.audio_queue.put(test_audio.tobytes())

        # Обработка одного элемента
        with patch('time.time', return_value=1000), \
             patch('time.sleep'):
            voice_engine._process_audio_queue()

        # Проверка, что модель была вызвана
        voice_engine.whisper_model.transcribe.assert_called_once()

    @patch('threading.Thread')
    def test_start_listening(self, mock_thread, voice_engine):
        """Тест запуска прослушивания."""
        voice_engine.recognizer.listen_in_background = Mock()

        voice_engine.start_listening()

        assert voice_engine.is_listening
        voice_engine.recognizer.listen_in_background.assert_called_once()
        mock_thread.assert_called_once()

    def test_stop_listening(self, voice_engine):
        """Тест остановки прослушивания."""
        voice_engine.is_listening = True
        voice_engine.stop_listening = Mock()

        voice_engine.stop_listening()

        assert not voice_engine.is_listening