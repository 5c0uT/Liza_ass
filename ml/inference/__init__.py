"""
Пакет инференса моделей для AI-ассистента Лиза.
"""

from .engine import InferenceEngine
from .optimizations import optimize_model, quantize_model

__all__ = ['InferenceEngine', 'optimize_model', 'quantize_model']