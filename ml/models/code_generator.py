"""
Модель генерации кода для AI-ассистента Лиза.
"""

import logging
import torch
import torch.nn as nn
from transformers import GPT2LMHeadModel, GPT2Tokenizer, GPT2Config
from typing import List, Dict, Any


class CodeGenerator(nn.Module):
    """Модель для генерации кода на основе естественно-языкового описания."""

    def __init__(self, model_name: str = "gpt2", max_length: int = 100,
                 temperature: float = 0.8, top_k: int = 50, top_p: float = 0.9):
        super(CodeGenerator, self).__init__()
        self.logger = logging.getLogger(__name__)

        self.model_name = model_name
        self.max_length = max_length
        self.temperature = temperature
        self.top_k = top_k
        self.top_p = top_p

        # Загрузка токенизатора и модели
        self.tokenizer = GPT2Tokenizer.from_pretrained(model_name)
        self.tokenizer.pad_token = self.tokenizer.eos_token

        # Конфигурация модели
        config = GPT2Config.from_pretrained(model_name)
        self.model = GPT2LMHeadModel.from_pretrained(model_name, config=config)

        # Добавление специальных токенов для программирования
        self._add_special_tokens()

    def _add_special_tokens(self):
        """Добавление специальных токенов для программирования."""
        special_tokens = {
            'additional_special_tokens': [
                '<python>', '</python>',
                '<javascript>', '</javascript>',
                '<java>', '</java>',
                '<html>', '</html>',
                '<css>', '</css>',
                '<sql>', '</sql>',
                '<function>', '</function>',
                '<class>', '</class>',
                '<loop>', '</loop>',
                '<condition>', '</condition>'
            ]
        }

        self.tokenizer.add_special_tokens(special_tokens)
        self.model.resize_token_embeddings(len(self.tokenizer))

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor = None,
                labels: torch.Tensor = None) -> Dict[str, torch.Tensor]:
        """
        Прямой проход через модель.

        Args:
            input_ids: ID токенов входного текста
            attention_mask: Маска внимания
            labels: Метки для обучения

        Returns:
            Выход модели с потерями и логитами
        """
        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels
        )

        return outputs

    def generate(self, prompt: str, language: str = "python",
                 max_length: int = None) -> str:
        """
        Генерация кода на основе промпта.

        Args:
            prompt: Текстовое описание кода
            language: Язык программирования
            max_length: Максимальная длина генерируемого текста

        Returns:
            Сгенерированный код
        """
        self.eval()

        # Подготовка промпта с языком
        full_prompt = f"<{language}>\n# {prompt}\n"

        # Токенизация
        input_ids = self.tokenizer.encode(full_prompt, return_tensors="pt")

        # Генерация
        with torch.no_grad():
            output = self.model.generate(
                input_ids,
                max_length=max_length or self.max_length,
                temperature=self.temperature,
                top_k=self.top_k,
                top_p=self.top_p,
                pad_token_id=self.tokenizer.eos_token_id,
                do_sample=True,
                num_return_sequences=1
            )

        # Декодирование
        generated_code = self.tokenizer.decode(output[0], skip_special_tokens=False)

        # Извлечение кода для указанного языка
        start_tag = f"<{language}>"
        end_tag = f"</{language}>"

        start_idx = generated_code.find(start_tag)
        end_idx = generated_code.find(end_tag)

        if start_idx != -1 and end_idx != -1:
            # Извлечение кода между тегами
            code_start = start_idx + len(start_tag)
            generated_code = generated_code[code_start:end_idx].strip()
        else:
            # Если теги не найдены, возвращаем весь текст после промпта
            generated_code = generated_code[len(full_prompt):].strip()

        return generated_code

    def fine_tune(self, dataset, epochs: int = 3, learning_rate: float = 5e-5,
                  batch_size: int = 4):
        """Тонкая настройка модели на специфичных данных."""
        from torch.utils.data import DataLoader
        from transformers import get_linear_schedule_with_warmup
        from torch.optim import AdamW
        # Подготовка DataLoader
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        # Оптимизатор и scheduler
        optimizer = AdamW(self.model.parameters(), lr=learning_rate)
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=0,
            num_training_steps=len(dataloader) * epochs
        )

        # Обучение
        self.model.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch_idx, batch in enumerate(dataloader):
                optimizer.zero_grad()

                # Forward pass
                outputs = self.forward(
                    input_ids=batch['input_ids'],
                    attention_mask=batch['attention_mask'],
                    labels=batch['labels']
                )

                # Backward pass
                loss = outputs.loss
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)

                optimizer.step()
                scheduler.step()

                total_loss += loss.item()

                if batch_idx % 100 == 0:
                    self.logger.info(
                        f"Epoch: {epoch + 1}/{epochs} "
                        f"Batch: {batch_idx}/{len(dataloader)} "
                        f"Loss: {loss.item():.6f}"
                    )

            avg_loss = total_loss / len(dataloader)
            self.logger.info(f"Epoch: {epoch + 1}/{epochs} Average Loss: {avg_loss:.6f}")