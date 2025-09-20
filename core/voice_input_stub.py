"""
Модуль голосового ввода с использованием SpeechRecognition и Whisper.
"""

import threading
import queue
import time
import logging
import numpy as np
import speech_recognition as sr
import whisper
from PyQt6.QtCore import QObject, pyqtSignal

class VoiceInputEngine(QObject):
    """Движок голосового ввода с непрерывным прослушиванием."""

    command_received = pyqtSignal(str)

    def __init__(self, model_size: str = "base", energy_threshold: int = 1000,
                 pause_threshold: float = 0.8, record_timeout: float = 2.0,
                 phrase_timeout: float = 3.0):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        self.model_size = model_size
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self.record_timeout = record_timeout
        self.phrase_timeout = phrase_timeout

        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.last_phrase_time = time.time()

        # Настройка параметров распознавания
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold
        self.recognizer.dynamic_energy_threshold = True

        # Загрузка модели Whisper
        try:
            self.logger.info(f"Загрузка модели Whisper ({model_size})...")
            self.whisper_model = whisper.load_model(model_size)
            self.logger.info("Модель Whisper успешно загружена")
        except Exception as e:
            self.logger.error(f"Не удалось загрузить модель Whisper: {e}")
            raise RuntimeError(f"Не удалось загрузить модель Whisper: {e}")

    def _adjust_microphone(self):
        """Настройка микрофона для окружающего шума."""
        try:
            with self.microphone as source:
                self.logger.info("Калибровка микрофона для окружающего шума...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.logger.info("Калибровка завершена")
        except Exception as e:
            self.logger.error(f"Ошибка калибровки микрофона: {e}")

    def _audio_callback(self, recognizer, audio):
        """Обратный вызов для обработки аудио."""
        try:
            # Получение raw audio data
            data = audio.get_raw_data()
            self.audio_queue.put(data)
        except Exception as e:
            self.logger.error(f"Ошибка в audio callback: {e}")

    def _process_audio_queue(self):
        """Фоновая обработка аудио из очереди."""
        while self.is_listening:
            try:
                # Получение аудио данных из очереди
                audio_data = self.audio_queue.get(timeout=1.0)

                # Конвертация в формат для Whisper
                audio_np = np.frombuffer(audio_data, dtype=np.int16)
                audio_np = audio_np.astype(np.float32) / 32768.0

                # Распознавание речи
                result = self.whisper_model.transcribe(audio_np, language='ru')
                text = result["text"].strip()

                if text:
                    self.logger.debug(f"Распознано: {text}")
                    current_time = time.time()

                    # Проверка таймаута между фразами
                    if current_time - self.last_phrase_time > self.phrase_timeout:
                        self.last_phrase_time = current_time
                        self.command_received.emit(text)

            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Ошибка обработки аудио: {e}")

    def start_listening(self):
        """Запуск непрерывного прослушивания."""
        if self.is_listening:
            self.logger.warning("Прослушивание уже запущено")
            return

        try:
            self.logger.info("Запуск прослушивания...")
            self._adjust_microphone()

            # Запуск фонового прослушивания
            self.stop_listening = self.recognizer.listen_in_background(
                self.microphone,
                self._audio_callback,
                phrase_time_limit=self.record_timeout
            )

            # Запуск обработки аудио в отдельном потоке
            self.is_listening = True
            self.process_thread = threading.Thread(target=self._process_audio_queue)
            self.process_thread.daemon = True
            self.process_thread.start()

            self.logger.info("Прослушивание запущено")

        except Exception as e:
            self.logger.error(f"Ошибка запуска прослушивания: {e}")
            raise

    def stop_listening(self):
        """Остановка прослушивания."""
        if not self.is_listening:
            return

        self.logger.info("Остановка прослушивания...")
        self.is_listening = False

        if hasattr(self, 'process_thread') and self.process_thread.is_alive():
            self.process_thread.join(timeout=2.0)

        if hasattr(self, 'stop_listening') and callable(self.stop_listening):
            self.stop_listening(wait_for_stop=False)

        self.logger.info("Прослушивание остановлено")