"""
Кастомные оптимизаторы для обучения моделей AI-ассистента Лиза.
"""

import torch
import torch.optim as optim
from typing import Dict, Any, Optional


class CustomOptimizer:
    """Фабрика кастомных оптимизаторов с расширенными возможностями."""

    @staticmethod
    def create_optimizer(model_params, optimizer_type: str = "adam",
                         lr: float = 0.001, **kwargs) -> optim.Optimizer:
        """
        Создание оптимизатора указанного типа.

        Args:
            model_params: Параметры модели для оптимизации
            optimizer_type: Тип оптимизатора (adam, sgd, rmsprop)
            lr: Learning rate
            **kwargs: Дополнительные параметры оптимизатора

        Returns:
            Экземпляр оптимизатора
        """
        optimizer_type = optimizer_type.lower()

        if optimizer_type == "adam":
            return optim.Adam(
                model_params,
                lr=lr,
                betas=kwargs.get('betas', (0.9, 0.999)),
                eps=kwargs.get('eps', 1e-8),
                weight_decay=kwargs.get('weight_decay', 0)
            )

        elif optimizer_type == "sgd":
            return optim.SGD(
                model_params,
                lr=lr,
                momentum=kwargs.get('momentum', 0),
                weight_decay=kwargs.get('weight_decay', 0),
                nesterov=kwargs.get('nesterov', False)
            )

        elif optimizer_type == "rmsprop":
            return optim.RMSprop(
                model_params,
                lr=lr,
                alpha=kwargs.get('alpha', 0.99),
                eps=kwargs.get('eps', 1e-8),
                weight_decay=kwargs.get('weight_decay', 0),
                momentum=kwargs.get('momentum', 0)
            )

        elif optimizer_type == "adagrad":
            return optim.Adagrad(
                model_params,
                lr=lr,
                lr_decay=kwargs.get('lr_decay', 0),
                weight_decay=kwargs.get('weight_decay', 0)
            )

        else:
            raise ValueError(f"Неизвестный тип оптимизатора: {optimizer_type}")

    @staticmethod
    def create_scheduler(optimizer: optim.Optimizer, scheduler_type: str = "step",
                         **kwargs) -> Optional[optim.lr_scheduler._LRScheduler]:
        """
        Создание scheduler для оптимизатора.

        Args:
            optimizer: Оптимизатор
            scheduler_type: Тип scheduler (step, plateau, cosine)
            **kwargs: Дополнительные параметры scheduler

        Returns:
            Экземпляр scheduler или None
        """
        if scheduler_type == "step":
            return optim.lr_scheduler.StepLR(
                optimizer,
                step_size=kwargs.get('step_size', 30),
                gamma=kwargs.get('gamma', 0.1)
            )

        elif scheduler_type == "plateau":
            return optim.lr_scheduler.ReduceLROnPlateau(
                optimizer,
                mode=kwargs.get('mode', 'min'),
                factor=kwargs.get('factor', 0.1),
                patience=kwargs.get('patience', 10),
                threshold=kwargs.get('threshold', 1e-4)
            )

        elif scheduler_type == "cosine":
            return optim.lr_scheduler.CosineAnnealingLR(
                optimizer,
                T_max=kwargs.get('T_max', 50),
                eta_min=kwargs.get('eta_min', 0)
            )

        elif scheduler_type == "cyclic":
            return optim.lr_scheduler.CyclicLR(
                optimizer,
                base_lr=kwargs.get('base_lr', 0.001),
                max_lr=kwargs.get('max_lr', 0.01),
                step_size_up=kwargs.get('step_size_up', 2000)
            )

        else:
            return None

    @staticmethod
    def create_optimizer_with_scheduler(model_params, optimizer_config: Dict[str, Any]):
        """
        Создание оптимизатора и scheduler по конфигурации.

        Args:
            model_params: Параметры модели
            optimizer_config: Конфигурация оптимизатора

        Returns:
            Кортеж (optimizer, scheduler)
        """
        optimizer = CustomOptimizer.create_optimizer(
            model_params,
            optimizer_config.get('type', 'adam'),
            optimizer_config.get('lr', 0.001),
            **optimizer_config.get('params', {})
        )

        scheduler_config = optimizer_config.get('scheduler')
        if scheduler_config:
            scheduler = CustomOptimizer.create_scheduler(
                optimizer,
                scheduler_config.get('type'),
                **scheduler_config.get('params', {})
            )
        else:
            scheduler = None

        return optimizer, scheduler