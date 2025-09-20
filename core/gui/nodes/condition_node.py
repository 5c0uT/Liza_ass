"""
Нода условия для workflow.
"""

from typing import Dict, Any
from core.gui.nodes.base_node import BaseNode
import ast
import operator as op


class ConditionNode(BaseNode):
    """Нода условия для ветвления workflow."""

    # Поддерживаемые операторы
    OPERATORS = {
        '==': op.eq,
        '!=': op.ne,
        '<': op.lt,
        '<=': op.le,
        '>': op.gt,
        '>=': op.ge,
        'contains': lambda a, b: b in a if hasattr(a, '__contains__') else False,
        'not contains': lambda a, b: b not in a if hasattr(a, '__contains__') else True,
        'is empty': lambda a: not bool(a),
        'is not empty': lambda a: bool(a),
        'is true': lambda a: bool(a),
        'is false': lambda a: not bool(a)
    }

    def __init__(self, parent=None):
        super().__init__("Условие", parent)

        # Добавление портов
        self.add_input("вход")
        self.add_input("значение1")
        self.add_input("значение2")
        self.add_output("истина")
        self.add_output("ложь")

        # Свойства по умолчанию
        self.set_property("mode", "expression")  # expression или comparison
        self.set_property("expression", "")
        self.set_property("value1", "")
        self.set_property("value2", "")
        self.set_property("operator", "==")
        self.set_property("strict_types", False)

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение условия."""
        mode = self.get_property("mode")
        strict_types = self.get_property("strict_types")

        try:
            if mode == "expression":
                result = self._evaluate_expression(inputs)
            else:
                result = self._evaluate_comparison(inputs)

            if result:
                return {"истина": "Условие истинно", "результат": result}
            else:
                return {"ложь": "Условие ложно", "результат": result}

        except Exception as e:
            error_msg = f"Ошибка оценки условия: {e}"
            self.logger.error(error_msg)
            return {"ложь": error_msg}

    def _evaluate_expression(self, inputs: Dict[str, Any]) -> bool:
        """Оценка выражения."""
        expression = self.get_property("expression")

        if not expression:
            raise ValueError("Выражение условия не задано")

        # Безопасная оценка выражения с использованием ast
        try:
            # Создаем безопасный контекст для выполнения
            safe_globals = {
                'True': True,
                'False': False,
                'None': None,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set
            }

            # Добавляем входные данные в контекст
            context = {**safe_globals, **inputs}

            # Парсим и компилируем выражение
            tree = ast.parse(expression, mode='eval')
            code = compile(tree, '<string>', 'eval')

            # Выполняем выражение
            result = eval(code, {'__builtins__': {}}, context)

            return bool(result)

        except Exception as e:
            self.logger.error(f"Ошибка оценки выражения '{expression}': {e}")
            raise

    def _evaluate_comparison(self, inputs: Dict[str, Any]) -> bool:
        """Оценка сравнения двух значений."""
        # Получаем значения и оператор
        value1 = self._get_value("value1", inputs)
        value2 = self._get_value("value2", inputs)
        operator_name = self.get_property("operator")

        # Получаем функцию оператора
        if operator_name not in self.OPERATORS:
            raise ValueError(f"Неизвестный оператор: {operator_name}")

        operator_func = self.OPERATORS[operator_name]

        # Выполняем сравнение
        try:
            return operator_func(value1, value2)
        except Exception as e:
            self.logger.error(f"Ошибка сравнения {value1} {operator_name} {value2}: {e}")
            raise

    def _get_value(self, value_key: str, inputs: Dict[str, Any]) -> Any:
        """Получение значения из свойства или входных данных."""
        value = self.get_property(value_key)

        # Если значение пустое, пытаемся получить из входных данных
        if not value and value_key in inputs:
            value = inputs[value_key]

        # Преобразуем типы если нужно
        strict_types = self.get_property("strict_types")
        if not strict_types and isinstance(value, str):
            # Пытаемся определить тип автоматически
            try:
                # Пробуем преобразовать в число
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
            except ValueError:
                # Пробуем преобразовать в булево значение
                if value.lower() in ('true', 'false'):
                    return value.lower() == 'true'
                # Оставляем как строку
                return value

        return value

    def get_available_operators(self) -> list:
        """Получение списка доступных операторов."""
        return list(self.OPERATORS.keys())

    def validate_expression(self, expression: str) -> bool:
        """Проверка валидности выражения."""
        try:
            ast.parse(expression, mode='eval')
            return True
        except:
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация ноды в словарь."""
        data = super().to_dict()
        # Добавляем информацию о поддерживаемых операторах
        data["operators"] = self.get_available_operators()
        return data