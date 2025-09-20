"""
Модуль голосового ввода с использованием SpeechRecognition.
"""

import speech_recognition as sr
import logging
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
import queue
import time

logger = logging.getLogger(__name__)

class VoiceInputWorker(QThread):
    """Рабочий поток для обработки голосового ввода."""

    command_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    listening_state_changed = pyqtSignal(bool)

    def __init__(self, energy_threshold=1000, pause_threshold=0.8, dynamic_energy_threshold=True):
        super().__init__()
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self.dynamic_energy_threshold = dynamic_energy_threshold
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold
        self.recognizer.dynamic_energy_threshold = dynamic_energy_threshold

        # Очередь для команд
        self.command_queue = queue.Queue()
        self.is_running = False

    def run(self):
        """Запуск потока для прослушивания."""
        self.is_running = True
        self.listening_state_changed.emit(True)

        # Инициализация микрофона
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                logger.info("Микрофон настроен, начинаю прослушивание")

                while self.is_running:
                    try:
                        # Слушаем аудио
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)

                        # Распознаем речь
                        try:
                            text = self.recognizer.recognize_google(audio, language="ru-RU")
                            if text.strip():
                                self.command_received.emit(text)
                                logger.info(f"Распознана команда: {text}")
                        except sr.UnknownValueError:
                            logger.debug("Речь не распознана")
                        except sr.RequestError as e:
                            self.error_occurred.emit(f"Ошибка сервиса распознавания: {e}")

                    except sr.WaitTimeoutError:
                        # Таймаут - нормальная ситуация, продолжаем слушать
                        continue
                    except Exception as e:
                        logger.error(f"Ошибка при прослушивании: {e}")

        except Exception as e:
            self.error_occurred.emit(f"Ошибка инициализации микрофона: {e}")
        finally:
            self.is_running = False
            self.listening_state_changed.emit(False)

    def stop(self):
        """Остановка потока."""
        self.is_running = False

class VoiceInputEngine(QObject):
    """Движок голосового ввода."""

    command_received = pyqtSignal(str)
    listening_started = pyqtSignal()
    listening_stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, energy_threshold=1000, pause_threshold=0.8, dynamic_energy_threshold=True):
        super().__init__()
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self.dynamic_energy_threshold = dynamic_energy_threshold
        self.worker = None
        self.is_listening = False

    def start_listening(self) -> bool:
        """Запуск прослушивания."""
        try:
            if self.worker and self.worker.isRunning():
                self.stop_listening()

            self.worker = VoiceInputWorker(
                self.energy_threshold,
                self.pause_threshold,
                self.dynamic_energy_threshold
            )

            self.worker.command_received.connect(self.command_received)
            self.worker.error_occurred.connect(self.error_occurred)
            self.worker.listening_state_changed.connect(self._on_listening_state_changed)

            self.worker.start()
            return True

        except Exception as e:
            self.error_occurred.emit(f"Ошибка запуска прослушивания: {e}")
            return False

    def stop_listening(self) -> bool:
        """Остановка прослушивания."""
        try:
            if self.worker and self.worker.isRunning():
                self.worker.stop()
                self.worker.wait(2000)  # Ждем до 2 секунд для завершения
                self.is_listening = False
            return True
        except Exception as e:
            self.error_occurred.emit(f"Ошибка остановки прослушивания: {e}")
            return False

    def _on_listening_state_changed(self, is_listening):
        """Обработка изменения состояния прослушивания."""
        self.is_listening = is_listening
        if is_listening:
            self.listening_started.emit()
        else:
            self.listening_stopped.emit()

    def set_energy_threshold(self, threshold: int):
        """Установка порога энергии."""
        self.energy_threshold = threshold
        if self.worker:
            self.worker.recognizer.energy_threshold = threshold

    def get_status(self) -> dict:
        """Получение статуса движка."""
        return {
            "is_listening": self.is_listening,
            "energy_threshold": self.energy_threshold,
            "pause_threshold": self.pause_threshold,
            "dynamic_energy_threshold": self.dynamic_energy_threshold
        }