"""
Оптимизации для инференса моделей AI-ассистента Лиза.
"""

import logging
import time

import torch
from typing import Dict, Any, Optional

# Добавляем импорт для статического квантования
try:
    from torch.quantization import quantize_dynamic, get_default_qconfig, prepare, convert
except ImportError:
    # Для более новых версий PyTorch
    from torch.ao.quantization import quantize_dynamic, get_default_qconfig, prepare, convert

logger = logging.getLogger(__name__)

def optimize_model(model: torch.nn.Module, optimization_level: str = "default") -> torch.nn.Module:
    """
    Оптимизация модели для ускорения инференса.

    Args:
        model: Модель для оптимизации
        optimization_level: Уровень оптимизации (minimal, default, aggressive)

    Returns:
        Оптимизированная модель
    """
    try:
        logger.info(f"Оптимизация модели с уровнем: {optimization_level}")

        # Переключение в eval mode
        model.eval()

        if optimization_level == "minimal":
            # Минимальная оптимизация - только torchscript
            model = torch.jit.script(model)

        elif optimization_level == "default":
            # Оптимизация по умолчанию
            with torch.no_grad():
                # Используем torch.compile если доступен (PyTorch 2.0+)
                if hasattr(torch, 'compile'):
                    model = torch.compile(model)
                else:
                    model = torch.jit.script(model)
                    model = torch.jit.optimize_for_inference(model)

        elif optimization_level == "aggressive":
            # Агрессивная оптимизация
            with torch.no_grad():
                # Quantization
                model = quantize_model(model)

                # Дополнительные оптимизации
                if hasattr(torch, 'compile'):
                    model = torch.compile(model, mode="max-autotune")
                else:
                    model = torch.jit.script(model)
                    model = torch.jit.optimize_for_inference(model)

        logger.info("Оптимизация модели завершена")
        return model

    except Exception as e:
        logger.error(f"Ошибка оптимизации модели: {e}")
        return model


def quantize_model(model: torch.nn.Module, quantization_type: str = "dynamic") -> torch.nn.Module:
    """
    Квантование модели для уменьшения размера и ускорения.

    Args:
        model: Модель для квантования
        quantization_type: Тип квантования (dynamic, static)

    Returns:
        Квантованная модель
    """
    try:
        logger.info(f"Квантование модели с типом: {quantization_type}")

        if quantization_type == "dynamic":
            # Динамическое квантование
            model = quantize_dynamic(
                model, {torch.nn.Linear}, dtype=torch.qint8
            )

        elif quantization_type == "static":
            # Статическое квантование (требует калибровки)
            # Определяем точки слияния для распространенных архитектур
            if hasattr(model, 'fuse_modules'):
                model.fuse_modules()

            # Настройка конфигурации квантования
            model.qconfig = get_default_qconfig('fbgemm')

            # Подготовка модели для квантования
            model = prepare(model)

            # Калибровка модели (нужно передать калибровочные данные)
            # Для простоты используем случайные данные
            with torch.no_grad():
                for _ in range(10):
                    # Создаем фиктивные входные данные для калибровки
                    # В реальном использовании нужно заменить на реальные данные
                    sample_input = torch.randn(1, 3, 224, 224)
                    model(sample_input)

            # Конвертация в квантованную модель
            model = convert(model)

        logger.info("Квантование модели завершено")
        return model

    except Exception as e:
        logger.error(f"Ошибка квантования модели: {e}")
        return model


def optimize_for_device(model: torch.nn.Module, device: str = "cpu") -> torch.nn.Module:
    """
    Оптимизация модели для конкретного устройства.

    Args:
        model: Модель для оптимизации
        device: Целевое устройство (cpu, cuda, mps)

    Returns:
        Оптимизированная модель
    """
    try:
        logger.info(f"Оптимизация модели для устройства: {device}")

        if device == "cpu":
            # Оптимизации для CPU
            torch.set_num_threads(torch.get_num_threads())
            model = optimize_model(model, "default")

        elif device == "cuda":
            # Оптимизации для CUDA
            model = model.to('cuda')
            if hasattr(torch, 'compile'):
                model = torch.compile(model, mode="reduce-overhead")
            else:
                model = torch.jit.script(model)

        elif device == "mps" and hasattr(torch.backends, 'mps'):
            # Оптимизации для MPS (Apple Silicon)
            model = model.to('mps')
            model = optimize_model(model, "minimal")
        else:
            logger.warning(f"Устройство {device} не поддерживается или не доступно")
            return model

        logger.info("Оптимизация для устройства завершена")
        return model

    except Exception as e:
        logger.error(f"Ошибка оптимизации для устройства: {e}")
        return model


def get_model_size(model: torch.nn.Module) -> Dict[str, Any]:
    """
    Получение информации о размере модели.

    Args:
        model: Модель для анализа

    Returns:
        Словарь с информацией о размере модели
    """
    try:
        param_size = 0
        for param in model.parameters():
            param_size += param.nelement() * param.element_size()

        buffer_size = 0
        for buffer in model.buffers():
            buffer_size += buffer.nelement() * buffer.element_size()

        size_all_mb = (param_size + buffer_size) / 1024**2

        return {
            'parameters_size_mb': param_size / 1024**2,
            'buffers_size_mb': buffer_size / 1024**2,
            'total_size_mb': size_all_mb,
            'num_parameters': sum(p.numel() for p in model.parameters())
        }
    except Exception as e:
        logger.error(f"Ошибка получения размера модели: {e}")
        return {}


def benchmark_model(model: torch.nn.Module, input_tensor: torch.Tensor, num_runs: int = 100) -> Dict[str, Any]:
    """
    Бенчмарк производительности модели.

    Args:
        model: Модель для тестирования
        input_tensor: Входной тензор для тестирования
        num_runs: Количество запусков для усреднения

    Returns:
        Словарь с результатами бенчмарка
    """
    try:
        # Warm-up
        with torch.no_grad():
            for _ in range(10):
                _ = model(input_tensor)

        # Benchmark
        start_time = torch.cuda.Event(enable_timing=True) if input_tensor.is_cuda else None
        end_time = torch.cuda.Event(enable_timing=True) if input_tensor.is_cuda else None

        if input_tensor.is_cuda:
            start_time.record()
        else:
            start_time = time.time()

        with torch.no_grad():
            for _ in range(num_runs):
                _ = model(input_tensor)

        if input_tensor.is_cuda:
            end_time.record()
            torch.cuda.synchronize()
            elapsed_time = start_time.elapsed_time(end_time) / 1000  # Convert to seconds
        else:
            end_time = time.time()
            elapsed_time = end_time - start_time

        avg_inference_time = elapsed_time / num_runs

        return {
            'avg_inference_time_seconds': avg_inference_time,
            'fps': 1 / avg_inference_time,
            'device': str(input_tensor.device)
        }
    except Exception as e:
        logger.error(f"Ошибка бенчмарка модели: {e}")
        return {}