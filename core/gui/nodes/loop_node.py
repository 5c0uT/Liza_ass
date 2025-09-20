"""
Нода цикла для workflow.
"""

from typing import Dict, Any, List
from core.gui.nodes.base_node import BaseNode


class LoopNode(BaseNode):
    """Нода цикла для повторяющихся операций."""

    def __init__(self, parent=None):
        super().__init__("Цикл", parent)

        # Добавление портов
        self.add_input("вход")
        self.add_input("коллекция")
        self.add_output("выход")
        self.add_output("элемент")
        self.add_output("завершено")

        # Свойства по умолчанию
        self.set_property("collection", "[]")
        self.set_property("variable", "item")
        self.set_property("max_iterations", 100)
        self.set_property("current_index", 0)
        self.set_property("is_completed", False)

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение цикла."""
        # Получаем коллекцию из входных данных или свойств
        collection_data = inputs.get("коллекция") or self.get_property("collection")
        variable_name = self.get_property("variable")
        max_iterations = self.get_property("max_iterations")
        current_index = self.get_property("current_index")
        is_completed = self.get_property("is_completed")

        # Если цикл уже завершен, возвращаем завершающий результат
        if is_completed:
            return {
                "выход": [],
                "элемент": None,
                "завершено": "Цикл уже завершен"
            }

        # Преобразуем коллекцию в список, если она в строковом формате
        try:
            if isinstance(collection_data, str):
                # Безопасное преобразование строки в список
                collection = eval(collection_data, {"__builtins__": None}, {})
            else:
                collection = list(collection_data)
        except Exception as e:
            return {"завершено": f"Ошибка обработки коллекции: {e}"}

        # Проверяем, что коллекция является итерируемым объектом
        if not hasattr(collection, '__iter__'):
            return {"завершено": "Коллекция не является итерируемым объектом"}

        # Вычисляем количество оставшихся итераций
        remaining_iterations = min(len(collection) - current_index, max_iterations)

        # Обрабатываем элементы коллекции
        results = []
        current_element = None

        for i in range(remaining_iterations):
            if current_index >= len(collection):
                break

            current_element = collection[current_index]
            current_index += 1

            # Добавляем элемент в результаты
            results.append(f"Обработан элемент {current_index}: {current_element}")

            # Обновляем свойство текущего индекса
            self.set_property("current_index", current_index)

            # Если достигнут конец коллекции, отмечаем цикл как завершенный
            if current_index >= len(collection):
                self.set_property("is_completed", True)
                break

        # Формируем результат выполнения
        if current_index >= len(collection):
            completion_message = "Цикл завершен"
            self.set_property("is_completed", True)
        else:
            completion_message = f"Цикл приостановлен, обработано {current_index} из {len(collection)} элементов"

        return {
            "выход": results,
            "элемент": current_element,
            "завершено": completion_message
        }

    def reset(self):
        """Сброс состояния цикла."""
        self.set_property("current_index", 0)
        self.set_property("is_completed", False)
        self.logger.info("Состояние цикла сброшено")

    def get_progress(self) -> float:
        """Получение прогресса выполнения цикла."""
        collection_data = self.get_property("collection")
        current_index = self.get_property("current_index")

        try:
            if isinstance(collection_data, str):
                collection = eval(collection_data, {"__builtins__": None}, {})
            else:
                collection = list(collection_data)

            if len(collection) > 0:
                return current_index / len(collection)
            else:
                return 0.0
        except:
            return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация ноды в словарь."""
        data = super().to_dict()
        data["properties"]["current_index"] = self.get_property("current_index")
        data["properties"]["is_completed"] = self.get_property("is_completed")
        return data

    def from_dict(self, data: Dict[str, Any]):
        """Десериализация ноды из словаря."""
        super().from_dict(data)
        self.set_property("current_index", data["properties"].get("current_index", 0))
        self.set_property("is_completed", data["properties"].get("is_completed", False))