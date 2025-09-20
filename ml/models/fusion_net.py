"""
Многомодальная нейросеть FusionNet для объединения текстовых, визуальных и аудио данных.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

class FusionNet(nn.Module):
    """Многомодальная нейросеть для объединения текстовых, визуальных и аудио данных."""

    def __init__(self, text_dim=768, visual_dim=2048, audio_dim=128,
                 hidden_dim=512, output_dim=256, num_heads=8, num_layers=3):
        super(FusionNet, self).__init__()

        self.text_dim = text_dim
        self.visual_dim = visual_dim
        self.audio_dim = audio_dim
        self.hidden_dim = hidden_dim

        # Проекционные слои для каждого типа данных
        self.text_projection = nn.Linear(text_dim, hidden_dim)
        self.visual_projection = nn.Linear(visual_dim, hidden_dim)
        self.audio_projection = nn.Linear(audio_dim, hidden_dim)

        # LayerNorm для стабилизации обучения
        self.text_norm = nn.LayerNorm(hidden_dim)
        self.visual_norm = nn.LayerNorm(hidden_dim)
        self.audio_norm = nn.LayerNorm(hidden_dim)

        # Трансформер для слияния модальностей
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim*4,
            batch_first=True,
            dropout=0.1
        )
        self.fusion_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # Выходные слои
        self.output_projection = nn.Linear(hidden_dim, output_dim)
        self.dropout = nn.Dropout(0.1)

        # Инициализация весов
        self._init_weights()

    def _init_weights(self):
        """Инициализация весов слоев."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    def forward(self, text_features, visual_features, audio_features):
        """
        Прямой проход через сеть.

        Args:
            text_features: Текстовые features [batch_size, text_dim]
            visual_features: Визуальные features [batch_size, visual_dim]
            audio_features: Аудио features [batch_size, audio_dim]

        Returns:
            output: Объединенные features [batch_size, output_dim]
        """
        # Проекция каждого типа features в общее пространство
        text_proj = F.relu(self.text_projection(text_features))
        text_proj = self.text_norm(text_proj)

        visual_proj = F.relu(self.visual_projection(visual_features))
        visual_proj = self.visual_norm(visual_proj)

        audio_proj = F.relu(self.audio_projection(audio_features))
        audio_proj = self.audio_norm(audio_proj)

        # Объединение features по dimension=1 (последовательность)
        combined = torch.stack([text_proj, visual_proj, audio_proj], dim=1)

        # Прохождение через трансформер
        fused = self.fusion_encoder(combined)

        # Усреднение по модальностям и проекция в выходное пространство
        output = self.output_projection(fused.mean(dim=1))
        output = self.dropout(output)

        return output

    def get_attention_weights(self, text_features, visual_features, audio_features):
        """
        Получение весов внимания для интерпретируемости.

        Returns:
            attention_weights: Веса внимания между модальностями
        """
        # Проекция features
        text_proj = F.relu(self.text_projection(text_features))
        visual_proj = F.relu(self.visual_projection(visual_features))
        audio_proj = F.relu(self.audio_projection(audio_features))

        combined = torch.stack([text_proj, visual_proj, audio_proj], dim=1)

        # Сохранение весов внимания
        attention_weights = []
        for layer in self.fusion_encoder.layers:
            # self-attention веса
            attn_output, attn_weights = layer.self_attn(
                combined, combined, combined,
                need_weights=True
            )
            attention_weights.append(attn_weights)

        return attention_weights