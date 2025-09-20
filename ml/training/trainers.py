"""
Тренеры моделей для AI-ассистента Лиза.
"""

import logging
import torch
import torch.nn as nn
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path


class ModelTrainer:
    """Базовый тренер моделей машинного обучения."""

    def __init__(self, model: nn.Module, device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        self.logger = logging.getLogger(__name__)
        self.model = model.to(device)
        self.device = device

        # История обучения
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'train_acc': [],
            'val_acc': []
        }

    def train(self, train_loader, val_loader, optimizer: torch.optim.Optimizer,
              criterion: nn.Module, num_epochs: int, scheduler: Optional = None,
              early_stopping_patience: int = None) -> Dict[str, List[float]]:
        """
        Обучение модели.

        Args:
            train_loader: DataLoader для обучения
            val_loader: DataLoader для валидации
            optimizer: Оптимизатор
            criterion: Функция потерь
            num_epochs: Количество эпох
            scheduler: Scheduler для learning rate
            early_stopping_patience: Терпимость для early stopping

        Returns:
            История обучения
        """
        best_val_loss = float('inf')
        patience_counter = 0

        for epoch in range(num_epochs):
            # Фаза обучения
            self.model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0

            for batch_idx, (data, target) in enumerate(train_loader):
                # Перемещение данных на device
                data = self._prepare_data(data)
                target = target.to(self.device)

                # Forward pass
                optimizer.zero_grad()
                output = self.model(data)
                loss = criterion(output, target)

                # Backward pass
                loss.backward()
                optimizer.step()

                # Статистика
                train_loss += loss.item()
                _, predicted = output.max(1)
                train_total += target.size(0)
                train_correct += predicted.eq(target).sum().item()

                if batch_idx % 100 == 0:
                    self.logger.info(
                        f"Epoch: {epoch + 1}/{num_epochs} "
                        f"Batch: {batch_idx}/{len(train_loader)} "
                        f"Loss: {loss.item():.6f}"
                    )

            # Фаза валидации
            val_loss, val_acc = self.validate(val_loader, criterion)

            # Обновление history
            train_loss_avg = train_loss / len(train_loader)
            train_acc = 100. * train_correct / train_total

            self.history['train_loss'].append(train_loss_avg)
            self.history['val_loss'].append(val_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_acc'].append(val_acc)

            self.logger.info(
                f"Epoch: {epoch + 1}/{num_epochs} "
                f"Train Loss: {train_loss_avg:.6f} "
                f"Train Acc: {train_acc:.2f}% "
                f"Val Loss: {val_loss:.6f} "
                f"Val Acc: {val_acc:.2f}%"
            )

            # Обновление scheduler
            if scheduler:
                if isinstance(scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
                    scheduler.step(val_loss)
                else:
                    scheduler.step()

            # Early stopping
            if early_stopping_patience:
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    # Сохранение лучшей модели
                    self.save_checkpoint(Path("best_model.pth"))
                else:
                    patience_counter += 1
                    if patience_counter >= early_stopping_patience:
                        self.logger.info(f"Early stopping на эпохе {epoch + 1}")
                        break

        return self.history

    def validate(self, val_loader, criterion: nn.Module) -> tuple:
        """Валидация модели."""
        self.model.eval()
        val_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for data, target in val_loader:
                data = self._prepare_data(data)
                target = target.to(self.device)

                output = self.model(data)
                loss = criterion(output, target)

                val_loss += loss.item()
                _, predicted = output.max(1)
                total += target.size(0)
                correct += predicted.eq(target).sum().item()

        val_loss_avg = val_loss / len(val_loader)
        val_acc = 100. * correct / total

        return val_loss_avg, val_acc

    def _prepare_data(self, data: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Подготовка данных для модели."""
        prepared_data = {}
        for key, value in data.items():
            if isinstance(value, torch.Tensor):
                prepared_data[key] = value.to(self.device)
            elif isinstance(value, dict):
                prepared_data[key] = {k: v.to(self.device) for k, v in value.items()}
            else:
                prepared_data[key] = value

        return prepared_data

    def save_checkpoint(self, path: Path):
        """Сохранение чекпоинта модели."""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'history': self.history
        }, path)
        self.logger.info(f"Чекпоинт сохранен: {path}")

    def load_checkpoint(self, path: Path):
        """Загрузка чекпоинта модели."""
        if path.exists():
            checkpoint = torch.load(path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.history = checkpoint['history']
            self.logger.info(f"Чекпоинт загружен: {path}")
        else:
            self.logger.warning(f"Чекпоинт не найден: {path}")

    def predict(self, data_loader):
        """Предсказание на данных."""
        self.model.eval()
        predictions = []
        targets = []

        with torch.no_grad():
            for data, target in data_loader:
                data = self._prepare_data(data)
                output = self.model(data)
                predictions.append(output)
                targets.append(target)

        return torch.cat(predictions), torch.cat(targets)