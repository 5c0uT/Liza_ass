"""
Пакет автоматизации для AI-ассистента Лиза.
Содержит модули для управления окнами, файлами, процессами и мониторинга системы.
"""

import json
import os
import logging
import importlib
from typing import Dict, Any, List, Optional
from datetime import datetime

from .window_manager import WindowManager
from .file_manager import FileManager
from .process_manager import ProcessManager
from .system_monitor import SystemMonitor


class AutomationManager:
    """Главный менеджер автоматизации, объединяющий все модули."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.window_manager = WindowManager()
        self.file_manager = FileManager()
        self.process_manager = ProcessManager()
        self.system_monitor = SystemMonitor()

        # Загрузка workflow
        self.workflows = {}
        self.load_workflows()

        # Контекст выполнения workflow
        self.execution_context = {}

    def load_workflows(self) -> None:
        """Загрузка всех workflow из папки workflows."""
        workflows_dir = "workflows"
        if not os.path.exists(workflows_dir):
            os.makedirs(workflows_dir)
            self.logger.info(f"Создана директория {workflows_dir}")
            return

        for filename in os.listdir(workflows_dir):
            if filename.endswith(".json"):
                workflow_id = filename[:-5]  # Убираем расширение .json
                try:
                    with open(os.path.join(workflows_dir, filename), "r", encoding="utf-8") as f:
                        workflow_data = json.load(f)
                        self.workflows[workflow_id] = workflow_data
                    self.logger.info(f"Загружен workflow: {workflow_id}")
                except Exception as e:
                    self.logger.error(f"Ошибка загрузки workflow {filename}: {e}")

    def execute_workflow(self, workflow_id: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Выполнение workflow по идентификатору."""
        if workflow_id not in self.workflows:
            error_msg = f"Workflow {workflow_id} не найден"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

        workflow = self.workflows[workflow_id]
        self.execution_context = parameters or {}

        # Добавляем служебную информацию в контекст
        self.execution_context["_workflow_id"] = workflow_id
        self.execution_context["_start_time"] = datetime.now().isoformat()

        try:
            # Выполняем ноды workflow
            results = self._execute_nodes(workflow.get("nodes", []))

            # Формируем результат выполнения
            end_time = datetime.now().isoformat()
            self.execution_context["_end_time"] = end_time

            return {
                "success": True,
                "results": results,
                "context": self.execution_context,
                "workflow_id": workflow_id,
                "start_time": self.execution_context["_start_time"],
                "end_time": end_time
            }

        except Exception as e:
            error_msg = f"Ошибка выполнения workflow {workflow_id}: {e}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg, "workflow_id": workflow_id}

    def _execute_nodes(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Выполнение последовательности нод workflow."""
        results = []

        for node in nodes:
            try:
                node_type = node.get("type")
                node_id = node.get("id")
                properties = node.get("properties", {})

                self.logger.info(f"Выполнение ноды {node_id} типа {node_type}")

                # Получаем входные данные для ноды
                inputs = self._prepare_node_inputs(node)

                # Выполняем ноду
                result = self._execute_node(node_type, properties, inputs)

                # Сохраняем результат в контекст выполнения
                if node_id:
                    self.execution_context[node_id] = result

                results.append({
                    "node_id": node_id,
                    "node_type": node_type,
                    "result": result,
                    "success": True
                })

            except Exception as e:
                error_msg = f"Ошибка выполнения ноды {node.get('id', 'unknown')}: {e}"
                self.logger.error(error_msg)
                results.append({
                    "node_id": node.get("id"),
                    "node_type": node.get("type"),
                    "result": None,
                    "success": False,
                    "error": error_msg
                })

                # Если нода критическая, прерываем выполнение
                if node.get("critical", False):
                    raise Exception(f"Критическая ошибка в ноде {node.get('id')}: {e}")

        return results

    def _prepare_node_inputs(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Подготовка входных данных для ноды."""
        inputs = {}

        # Обрабатываем входные связи
        for input_name, connection in node.get("inputs", {}).items():
            if isinstance(connection, dict) and "node_id" in connection and "output" in connection:
                # Получаем данные из предыдущей ноды
                source_node_id = connection["node_id"]
                source_output = connection["output"]

                if source_node_id in self.execution_context:
                    source_result = self.execution_context[source_node_id]
                    if isinstance(source_result, dict) and source_output in source_result:
                        inputs[input_name] = source_result[source_output]
                    else:
                        inputs[input_name] = source_result
                else:
                    self.logger.warning(f"Не найдены данные от ноды {source_node_id}")

        # Добавляем свойства ноды как входные данные
        inputs.update(node.get("properties", {}))

        # Добавляем глобальный контекст выполнения
        inputs["_context"] = self.execution_context

        return inputs

    def _execute_node(self, node_type: str, properties: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        """Выполнение конкретной ноды по ее типу."""
        # Встроенные ноды
        if node_type == "command":
            return self._execute_command_node(properties, inputs)
        elif node_type == "condition":
            return self._execute_condition_node(properties, inputs)
        elif node_type == "loop":
            return self._execute_loop_node(properties, inputs)
        elif node_type == "window_operation":
            return self.window_manager.execute_operation(properties, inputs)
        elif node_type == "file_operation":
            return self.file_manager.execute_operation(properties, inputs)
        elif node_type == "process_operation":
            return self.process_manager.execute_operation(properties, inputs)
        elif node_type == "system_operation":
            return self.system_monitor.execute_operation(properties, inputs)
        else:
            # Попытка загрузить пользовательскую ноду
            return self._execute_custom_node(node_type, properties, inputs)

    def _execute_command_node(self, properties: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение ноды команды."""
        command = properties.get("command", "")
        command_type = properties.get("command_type", "system")
        timeout = properties.get("timeout", 30)

        # Подставляем переменные из входных данных
        formatted_command = self._replace_variables(command, inputs)

        if command_type == "system":
            result = self.process_manager.execute_system_command(formatted_command, timeout)
        elif command_type == "python":
            result = self._execute_python_code(formatted_command, inputs)
        else:
            result = {"output": formatted_command, "success": True}

        return result

    def _execute_condition_node(self, properties: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение ноды условия."""
        condition = properties.get("condition", "")
        operator = properties.get("operator", "==")

        try:
            # Подставляем переменные в условие
            formatted_condition = self._replace_variables(condition, inputs)

            # Вычисляем условие
            result = self._evaluate_condition(formatted_condition, operator, inputs)

            return {
                "result": result,
                "branch": "true" if result else "false"
            }

        except Exception as e:
            self.logger.error(f"Ошибка оценки условия: {e}")
            return {"result": False, "branch": "false", "error": str(e)}

    def _execute_loop_node(self, properties: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение ноды цикла."""
        collection = properties.get("collection", "[]")
        variable = properties.get("variable", "item")
        max_iterations = properties.get("max_iterations", 100)

        try:
            # Получаем коллекцию для итерации
            if isinstance(collection, str):
                # Пытаемся получить коллекцию из контекста
                collection_value = inputs.get(collection, collection)
                # Если это все еще строка, пытаемся вычислить
                if isinstance(collection_value, str):
                    collection_value = eval(collection_value, {"__builtins__": None}, inputs)
            else:
                collection_value = collection

            # Преобразуем в список для итерации
            if not hasattr(collection_value, '__iter__'):
                collection_value = [collection_value]

            results = []
            iteration_count = 0

            # Выполняем итерации
            for item in collection_value:
                if iteration_count >= max_iterations:
                    break

                # Добавляем элемент в контекст
                iteration_context = inputs.copy()
                iteration_context[variable] = item
                iteration_context["_iteration"] = iteration_count

                # Выполняем дочерние ноды (если есть)
                child_nodes = properties.get("children", [])
                if child_nodes:
                    child_results = self._execute_nodes(child_nodes)
                    results.append({
                        "iteration": iteration_count,
                        "item": item,
                        "results": child_results
                    })
                else:
                    results.append({
                        "iteration": iteration_count,
                        "item": item
                    })

                iteration_count += 1

            return {
                "completed": True,
                "iterations": iteration_count,
                "results": results
            }

        except Exception as e:
            self.logger.error(f"Ошибка выполнения цикла: {e}")
            return {
                "completed": False,
                "error": str(e),
                "iterations": 0,
                "results": []
            }

    def _execute_custom_node(self, node_type: str, properties: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        """Выполнение пользовательской ноды."""
        try:
            # Пытаемся загрузить модуль пользовательской ноды
            module_name = f"custom_nodes.{node_type}"
            module = importlib.import_module(module_name)

            # Получаем класс ноды (предполагаем, что класс имеет то же имя, что и тип)
            node_class = getattr(module, node_type)

            # Создаем экземпляр ноды и выполняем
            node_instance = node_class()
            return node_instance.execute(properties, inputs)

        except ImportError:
            self.logger.error(f"Не найден модуль для пользовательской ноды: {node_type}")
            raise Exception(f"Неизвестный тип ноды: {node_type}")
        except Exception as e:
            self.logger.error(f"Ошибка выполнения пользовательской ноды {node_type}: {e}")
            raise

    def _replace_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Замена переменных в тексте на значения из контекста."""
        if not isinstance(text, str):
            return text

        for key, value in context.items():
            if isinstance(value, (str, int, float, bool)):
                placeholder = "{" + key + "}"
                if placeholder in text:
                    text = text.replace(placeholder, str(value))

        return text

    def _evaluate_condition(self, condition: str, operator: str, context: Dict[str, Any]) -> bool:
        """Оценка условия."""
        # Простая реализация для демонстрации
        # В реальной системе следует использовать безопасную оценку выражений

        if operator == "==":
            return condition == "True" or condition == "true"
        elif operator == "!=":
            return condition != "True" and condition != "true"
        elif operator == "contains":
            return "true" in condition.lower()
        else:
            # По умолчанию считаем условие истинным, если оно не пустое
            return bool(condition)

    def _execute_python_code(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Безопасное выполнение Python кода."""
        try:
            # Ограниченный контекст выполнения
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
                    'range': range
                }
            }

            # Добавляем контекст в глобальные переменные
            exec_globals = {**safe_globals, **context}

            # Выполняем код
            exec(code, exec_globals)

            # Ищем результат
            result = exec_globals.get('result', None)

            return {
                "output": result,
                "success": True
            }

        except Exception as e:
            self.logger.error(f"Ошибка выполнения Python кода: {e}")
            return {
                "output": None,
                "success": False,
                "error": str(e)
            }

    def get_workflow_list(self) -> List[Dict[str, Any]]:
        """Получение списка всех доступных workflow."""
        workflows = []

        for workflow_id, workflow_data in self.workflows.items():
            workflows.append({
                "id": workflow_id,
                "name": workflow_data.get("name", workflow_id),
                "description": workflow_data.get("description", ""),
                "version": workflow_data.get("version", "1.0"),
                "created": workflow_data.get("created", ""),
                "modified": workflow_data.get("modified", "")
            })

        return workflows

    def create_workflow(self, workflow_id: str, workflow_data: Dict[str, Any]) -> bool:
        """Создание нового workflow."""
        workflows_dir = "workflows"
        os.makedirs(workflows_dir, exist_ok=True)

        file_path = os.path.join(workflows_dir, f"{workflow_id}.json")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(workflow_data, f, indent=2, ensure_ascii=False)

            # Обновляем кэш workflow
            self.workflows[workflow_id] = workflow_data
            self.logger.info(f"Создан workflow: {workflow_id}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка создания workflow {workflow_id}: {e}")
            return False

    def delete_workflow(self, workflow_id: str) -> bool:
        """Удаление workflow."""
        workflows_dir = "workflows"
        file_path = os.path.join(workflows_dir, f"{workflow_id}.json")

        try:
            if os.path.exists(file_path):
                os.remove(file_path)

                # Удаляем из кэша
                if workflow_id in self.workflows:
                    del self.workflows[workflow_id]

                self.logger.info(f"Удален workflow: {workflow_id}")
                return True
            else:
                self.logger.warning(f"Workflow {workflow_id} не найден для удаления")
                return False

        except Exception as e:
            self.logger.error(f"Ошибка удаления workflow {workflow_id}: {e}")
            return False