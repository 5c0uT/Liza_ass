"""
Датасеты для обучения моделей AI-ассистента Лиза.
"""

import logging
import torch
from torch.utils.data import Dataset
from typing import List, Dict, Any, Tuple
import json
from pathlib import Path


class MultimodalDataset(Dataset):
    """Многомодальный датасет для обучения FusionNet."""

    def __init__(self, data_dir: str, split: str = "train", max_samples: int = None):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(data_dir)
        self.split = split
        self.max_samples = max_samples

        # Загрузка данных
        self.data = self._load_data()

    def _load_data(self) -> List[Dict[str, Any]]:
        """Загрузка данных из файлов."""
        data_file = self.data_dir / f"{self.split}.json"

        if not data_file.exists():
            self.logger.error(f"Файл данных не найден: {data_file}")
            return []

        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if self.max_samples:
                data = data[:self.max_samples]

            self.logger.info(f"Загружено {len(data)} samples для {self.split}")
            return data

        except Exception as e:
            self.logger.error(f"Ошибка загрузки данных: {e}")
            return []

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Tuple[Dict[str, torch.Tensor], torch.Tensor]:
        """Получение sample по индексу."""
        sample = self.data[idx]

        try:
            # Загрузка и подготовка features
            text_features = self._load_text_features(sample.get('text_features', []))
            visual_features = self._load_visual_features(sample.get('visual_features', []))
            audio_features = self._load_audio_features(sample.get('audio_features', []))

            # Подготовка target
            target = torch.tensor(sample.get('target', 0), dtype=torch.long)

            return {
                'text': text_features,
                'visual': visual_features,
                'audio': audio_features
            }, target

        except Exception as e:
            self.logger.error(f"Ошибка подготовки sample {idx}: {e}")
            # Возврат пустого sample в случае ошибки
            return {
                'text': torch.zeros(768),
                'visual': torch.zeros(2048),
                'audio': torch.zeros(128)
            }, torch.tensor(0)

    def _load_text_features(self, features: List[float]) -> torch.Tensor:
        """Загрузка текстовых features."""
        return torch.tensor(features, dtype=torch.float32)

    def _load_visual_features(self, features: List[float]) -> torch.Tensor:
        """Загрузка визуальных features."""
        return torch.tensor(features, dtype=torch.float32)

    def _load_audio_features(self, features: List[float]) -> torch.Tensor:
        """Загрузка аудио features."""
        return torch.tensor(features, dtype=torch.float32)

    def get_class_weights(self) -> torch.Tensor:
        """Получение весов классов для несбалансированных данных."""
        # Подсчет количества samples каждого класса
        class_counts = {}
        for sample in self.data:
            target = sample.get('target', 0)
            class_counts[target] = class_counts.get(target, 0) + 1

        # Вычисление весов
        total = len(self.data)
        weights = torch.zeros(max(class_counts.keys()) + 1 if class_counts else 1)

        for class_id, count in class_counts.items():
            weights[class_id] = total / (len(class_counts) * count)

        return weights