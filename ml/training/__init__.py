"""
Пакет обучения моделей для AI-ассистента Лиза.
"""

from .trainers import ModelTrainer
from .datasets import MultimodalDataset
from .optimizers import CustomOptimizer

__all__ = ['ModelTrainer', 'MultimodalDataset', 'CustomOptimizer']