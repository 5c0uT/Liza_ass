"""
Пакет машинного обучения для AI-ассистента Лиза.
Содержит модели, обучение и инференс.
"""

from .models.fusion_net import FusionNet
from .models.action_predictor import ActionPredictor
from .models.code_generator import CodeGenerator

from .training.trainers import ModelTrainer
from .training.datasets import MultimodalDataset
from .training.optimizers import CustomOptimizer

from .inference.engine import InferenceEngine
from .inference.optimizations import optimize_model

__version__ = "1.0.0"