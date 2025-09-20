"""
Модель предсказания действий для AI-ассистента Лиза.
"""

import logging
import torch
import torch.nn as nn
from typing import Dict, Any, List


class ActionPredictor(nn.Module):
    """Модель для предсказания следующих действий пользователя."""

    def __init__(self, input_dim: int = 256, hidden_dim: int = 128,
                 num_actions: int = 50, num_layers: int = 2, dropout: float = 0.1):
        super(ActionPredictor, self).__init__()
        self.logger = logging.getLogger(__name__)

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_actions = num_actions
        self.num_layers = num_layers

        # Многослойная LSTM для временных последовательностей
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

        # Attention механизм
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=4,
            dropout=dropout,
            batch_first=True
        )

        # Классификатор действий
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_actions)
        )

        # Dropout
        self.dropout = nn.Dropout(dropout)

        # Инициализация весов
        self._init_weights()

    def _init_weights(self):
        """Инициализация весов слоев."""
        for name, param in self.named_parameters():
            if 'weight' in name and param.dim() > 1:
                nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.zeros_(param)

    def forward(self, x: torch.Tensor, hidden: tuple = None) -> Dict[str, torch.Tensor]:
        """
        Прямой проход через модель.

        Args:
            x: Входные данные [batch_size, seq_len, input_dim]
            hidden: Скрытое состояние LSTM

        Returns:
            Словарь с предсказаниями и скрытым состоянием
        """
        batch_size, seq_len, _ = x.size()

        # LSTM
        lstm_out, hidden = self.lstm(x, hidden)
        lstm_out = self.dropout(lstm_out)

        # Attention
        attn_out, attn_weights = self.attention(
            lstm_out, lstm_out, lstm_out
        )
        attn_out = self.dropout(attn_out)

        # Используем только последний выход для классификации
        last_out = attn_out[:, -1, :]

        # Классификация
        logits = self.classifier(last_out)

        return {
            'logits': logits,
            'hidden': hidden,
            'attention_weights': attn_weights
        }

    def predict(self, x: torch.Tensor, hidden: tuple = None,
                top_k: int = 5) -> Dict[str, Any]:
        """
        Предсказание действий с вероятностями.

        Args:
            x: Входные данные
            hidden: Скрытое состояние
            top_k: Количество лучших предсказаний

        Returns:
            Словарь с предсказаниями
        """
        self.eval()
        with torch.no_grad():
            output = self.forward(x, hidden)
            logits = output['logits']

            # Softmax для вероятностей
            probs = torch.softmax(logits, dim=-1)
            top_probs, top_indices = torch.topk(probs, top_k, dim=-1)

            return {
                'probabilities': top_probs.cpu().numpy(),
                'indices': top_indices.cpu().numpy(),
                'hidden': output['hidden']
            }

    def get_attention_map(self, x: torch.Tensor) -> torch.Tensor:
        """Получение карты внимания для интерпретируемости."""
        self.eval()
        with torch.no_grad():
            output = self.forward(x)
            return output['attention_weights']