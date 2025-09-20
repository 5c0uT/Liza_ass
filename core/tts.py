"""
Модуль синтеза речи с использованием Silero TTS.
"""

import logging
import torch
from pathlib import Path
from typing import Optional
import io
import wave

class TTSEngine:
    """Движок синтеза речи на основе Silero TTS."""

    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        self.logger = logging.getLogger(__name__)
        self.device = device
        self.model = None
        self.sample_rate = 24000  # Исправлено: 24000 вместо 16000
        self.speaker = "aidar"  # По умолчанию мужской голос

        try:
            self._load_model(model_path)
            self.logger.info("Модель TTS успешно загружена")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки модели TTS: {e}")
            raise

    def _load_model(self, model_path: Optional[str] = None):
        """Загрузка модели TTS."""
        try:
            if model_path and Path(model_path).exists():
                # Загрузка кастомной модели
                self.model = torch.package.PackageImporter(model_path).load_pickle("tts_models", "model")
            else:
                # Загрузка стандартной модели Silero
                self.model, self.model_example = torch.hub.load(
                    repo_or_dir='snakers4/silero-models',
                    model='silero_tts',
                    language='ru',
                    speaker='ru_v3'
                )

            self.model.to(self.device)

        except Exception as e:
            self.logger.error(f"Ошибка загрузки модели TTS: {e}")
            raise RuntimeError(f"Не удалось загрузить модель TTS: {e}")

    def speak(self, text: str, speaker: Optional[str] = None) -> bool:
        """Синтез речи из текста."""
        if not self.model:
            self.logger.error("Модель TTS не загружена")
            return False

        try:
            if not text.strip():
                self.logger.warning("Пустой текст для синтеза речи")
                return False

            # Выбор голоса
            current_speaker = speaker or self.speaker

            # Синтез речи с использованием правильного API
            audio = self.model.apply_tts(
                text=text,
                speaker=current_speaker,
                sample_rate=self.sample_rate,
                put_accent=True,
                put_yo=True
            )

            # Воспроизведение аудио
            self._play_audio(audio)
            return True

        except Exception as e:
            self.logger.error(f"Ошибка синтеза речи: {e}")
            return False

    def _play_audio(self, audio):
        """Воспроизведение аудио через системный аудиовыход."""
        try:
            import sounddevice as sd
            sd.play(audio, self.sample_rate)
            sd.wait()
        except ImportError:
            self.logger.warning("SoundDevice не установлен, воспроизведение недоступно")
            # Альтернатива: использование pygame для воспроизведения
            self._play_audio_with_pygame(audio)
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения аудио: {e}")
            self._play_audio_with_pygame(audio)

    def _play_audio_with_pygame(self, audio):
        """Альтернативное воспроизведение аудио через pygame."""
        try:
            import pygame
            import numpy as np

            # Инициализация pygame mixer
            pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1)

            # Преобразование аудио в формат для pygame
            audio_int = (audio * 32767).astype(np.int16)
            sound = pygame.sndarray.make_sound(audio_int)

            # Воспроизведение
            sound.play()
            pygame.time.wait(int(len(audio) / self.sample_rate * 1000))

        except ImportError:
            self.logger.warning("Pygame не установлен, воспроизведение недоступно")
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения аудио через pygame: {e}")

    def save_to_file(self, text: str, filename: str, speaker: Optional[str] = None) -> bool:
        """Сохранение синтезированной речи в файл."""
        if not self.model:
            return False

        try:
            current_speaker = speaker or self.speaker

            audio = self.model.apply_tts(
                text=text,
                speaker=current_speaker,
                sample_rate=self.sample_rate,
                put_accent=True,
                put_yo=True
            )

            # Сохранение в WAV файл
            import scipy.io.wavfile as wav
            wav.write(filename, self.sample_rate, audio.numpy())

            return True

        except Exception as e:
            self.logger.error(f"Ошибка сохранения аудио в файл: {e}")
            return False

    def set_speaker(self, speaker: str) -> bool:
        """Установка голоса для синтеза."""
        available_speakers = ['aidar', 'baya', 'kseniya', 'xenia', 'eugene']

        if speaker not in available_speakers:
            self.logger.error(f"Неизвестный голос: {speaker}")
            return False

        self.speaker = speaker
        return True

    def get_available_speakers(self) -> list:
        """Получение списка доступных голосов."""
        return ['aidar', 'baya', 'kseniya', 'xenia', 'eugene']