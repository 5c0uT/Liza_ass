"""
Нода для выполнения команд в workflow.
"""

from typing import Dict, Any
from core.gui.nodes.base_node import BaseNode
import subprocess
import shlex
import threading
import time
import ast


class CommandNode(BaseNode):
    """Нода для выполнения команд."""

    def __init__(self, parent=None):
        super().__init__("Команда", parent)

        # Добавление портов
        self.add_input("вход")
        self.add_output("успех")
        self.add_output("ошибка")
        self.add_output("результат")

        # Свойства по умолчанию
        self.set_property("command_type", "system")  # system, python, или custom
        self.set_property("command", "")
        self.set_property("timeout", 30)
        self.set_property("working_dir", "")
        self.set_property("capture_output", True)
        self.set_property("shell", False)

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение команды."""
        command_type = self.get_property("command_type")
        timeout = self.get_property("timeout")

        try:
            # Подготавливаем команду с учетом входных данных
            command = self._prepare_command(inputs)

            if command_type == "system":
                result = self._execute_system_command(command, timeout)
            elif command_type == "python":
                result = self._execute_python_command(command, inputs)
            elif command_type == "custom":
                result = self._execute_custom_command(command, inputs)
            else:
                raise ValueError(f"Неизвестный тип команды: {command_type}")

            return {
                "успех": f"Команда выполнена успешно: {result.get('message', '')}",
                "результат": result.get("output", "")
            }

        except Exception as e:
            error_msg = f"Ошибка выполнения команды: {e}"
            self.logger.error(error_msg)
            return {"ошибка": error_msg}

    def _prepare_command(self, inputs: Dict[str, Any]) -> str:
        """Подготовка команды с подстановкой переменных из входных данных."""
        command_template = self.get_property("command")

        if not command_template:
            raise ValueError("Команда не задана")

        # Заменяем переменные в формате {var_name} на значения из входных данных
        try:
            # Простая подстановка переменных
            for key, value in inputs.items():
                placeholder = "{" + key + "}"
                if placeholder in command_template:
                    command_template = command_template.replace(placeholder, str(value))

            return command_template
        except Exception as e:
            self.logger.error(f"Ошибка подготовки команды: {e}")
            raise

    def _execute_system_command(self, command: str, timeout: int) -> Dict[str, Any]:
        """Выполнение системной команды."""
        working_dir = self.get_property("working_dir")
        capture_output = self.get_property("capture_output")
        use_shell = self.get_property("shell")

        try:
            # Разбиваем команду на аргументы, если не используется shell
            if not use_shell:
                command_args = shlex.split(command)
            else:
                command_args = command

            # Выполняем команду
            result = subprocess.run(
                command_args,
                cwd=working_dir if working_dir else None,
                shell=use_shell,
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )

            # Формируем результат
            output = {
                "returncode": result.returncode,
                "stdout": result.stdout if capture_output else "",
                "stderr": result.stderr if capture_output else "",
                "message": f"Команда выполнена с кодом возврата {result.returncode}"
            }

            # Проверяем код возврата
            if result.returncode != 0:
                raise Exception(f"Код возврата: {result.returncode}, stderr: {result.stderr}")

            return output

        except subprocess.TimeoutExpired:
            raise Exception(f"Таймаут выполнения команды ({timeout} секунд)")
        except FileNotFoundError:
            raise Exception(f"Команда или программа не найдена: {command}")
        except Exception as e:
            raise Exception(f"Ошибка выполнения системной команды: {e}")

    def _execute_python_command(self, command: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение Python-кода."""
        try:
            # Создаем безопасный контекст для выполнения
            safe_globals = {
                '__builtins__': {
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'range': range,
                    'min': min,
                    'max': max,
                    'sum': sum
                }
            }

            # Добавляем входные данные в контекст
            context = {**safe_globals, **inputs}

            # Парсим и выполняем код
            tree = ast.parse(command, mode='exec')
            code = compile(tree, '<string>', 'exec')

            # Выполняем код и захватываем результат
            exec(code, context)

            # Ищем переменную result в контексте
            result = context.get('result', None)

            return {
                "output": result,
                "message": "Python код выполнен успешно"
            }

        except Exception as e:
            raise Exception(f"Ошибка выполнения Python кода: {e}")

    def _execute_custom_command(self, command: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение пользовательской команды (можно расширить для плагинов)."""
        # В этой реализации просто возвращаем команду как результат
        # Можно расширить для поддержки плагинов или пользовательских обработчиков
        return {
            "output": command,
            "message": "Пользовательская команда выполнена"
        }

    def interrupt(self):
        """Прерывание выполнения команды."""
        # Можно реализовать прерывание длительных операций
        if hasattr(self, '_process') and self._process:
            try:
                self._process.terminate()
            except:
                pass

    def validate_command(self) -> bool:
        """Проверка валидности команды."""
        command = self.get_property("command")
        command_type = self.get_property("command_type")

        if not command:
            return False

        if command_type == "python":
            try:
                ast.parse(command)
                return True
            except:
                return False

        return True

    def get_command_types(self) -> list:
        """Получение списка доступных типов команд."""
        return ["system", "python", "custom"]

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация ноды в словарь."""
        data = super().to_dict()
        data["command_types"] = self.get_command_types()
        return data