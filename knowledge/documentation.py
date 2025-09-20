"""
Модуль автодокументирования для AI-ассистента Лиза.
"""

import logging
import ast
import inspect
import re
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from collections import Counter


class DocumentationGenerator:
    """Генератор документации для кода и процессов."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._russian_stopwords = {
            "и", "в", "на", "с", "по", "для", "не", "что", "это", "как",
            "из", "у", "к", "до", "от", "о", "же", "за", "бы", "по", "со",
            "то", "мне", "все", "так", "его", "вот", "от", "из", "ему",
            "тебя", "нас", "вас", "их", "чем", "при", "да", "нет", "если",
            "когда", "где", "куда", "кто", "что", "какой", "который", "этот",
            "тот", "такой", "там", "тут", "здесь", "опять", "уже", "еще",
            "опять", "очень", "можно", "нужно", "надо", "есть", "нет", "был",
            "была", "было", "были", "будет", "будут", "стал", "стала", "стало"
        }

    def generate_code_documentation(self, code: str, language: str = "python") -> str:
        """
        Генерация документации для кода.

        Args:
            code: Исходный код
            language: Язык программирования

        Returns:
            Сгенерированная документация
        """
        if language == "python":
            return self._generate_python_docs(code)
        else:
            return self._generate_general_docs(code, language)

    def _generate_python_docs(self, code: str) -> str:
        """Генерация документации для Python кода."""
        try:
            # Парсинг AST
            tree = ast.parse(code)

            docs = []

            # Поиск функций и классов
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_doc = self._document_function(node)
                    docs.append(func_doc)
                elif isinstance(node, ast.ClassDef):
                    class_doc = self._document_class(node)
                    docs.append(class_doc)

            return "\n\n".join(docs) if docs else "# Документация\n\nНе найдено классов или функций для документирования"
        except Exception as e:
            self.logger.error(f"Ошибка генерации Python документации: {e}")
            return f"# Документация\n\nНе удалось сгенерировать документацию: {e}"

    def _document_function(self, func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> str:
        """Документирование функции."""
        docstring = ast.get_docstring(func_node) or "Отсутствует описание"
        is_async = isinstance(func_node, ast.AsyncFunctionDef)
        func_type = "Асинхронная функция" if is_async else "Функция"

        # Получение аргументов с типами
        args_info = []
        for arg in func_node.args.args:
            arg_info = arg.arg
            if arg.annotation:
                arg_info += f": {ast.unparse(arg.annotation)}"
            args_info.append(arg_info)

        # Получение возвращаемого значения
        returns = "None"
        if func_node.returns:
            returns = ast.unparse(func_node.returns)

        return f"""### {func_type} {func_node.name}

{docstring}

**Аргументы:**
- {', '.join(args_info) if args_info else 'Нет аргументов'}

**Возвращает:**
{returns}
"""

    def _document_class(self, class_node: ast.ClassDef) -> str:
        """Документирование класса."""
        docstring = ast.get_docstring(class_node) or "Отсутствует описание"

        # Поиск методов
        methods = []
        for node in class_node.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(node.name)

        return f"""### Класс {class_node.name}

{docstring}

**Методы:**
- {', '.join(methods) if methods else 'Нет методов'}
"""

    def _generate_general_docs(self, code: str, language: str) -> str:
        """Генерация общей документации для других языков."""
        return f"""# Документация для {language} кода

```{language}
{code}
        Сгенерировано автоматически
        """

        text

        def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
            """
            Извлечение ключевых слов из текста.

            Args:
                text: Текст для анализа
                max_keywords: Максимальное количество ключевых слов

            Returns:
                Список ключевых слов
            """
            # Простая токенизация без nltk
            words = re.findall(r'\b[а-яa-z]{3,}\b', text.lower())

            # Фильтрация стоп-слов
            words = [word for word in words if word not in self._russian_stopwords]

            # Подсчет частотности и извлечение ключевых слов
            counter = Counter(words)
            return [word for word, count in counter.most_common(max_keywords)]

        def summarize_text(self, text: str, max_sentences: int = 3) -> str:
            """
            Суммаризация текста.

            Args:
                text: Текст для суммаризации
                max_sentences: Максимальное количество предложений

            Returns:
                Суммаризированный текст
            """
            # Простое разделение на предложения по точкам, вопросительным и восклицательным знакам
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]

            # Выбор первых N предложений
            return '. '.join(sentences[:max_sentences]) + '.'

        def generate_module_overview(self, file_path: Path) -> Optional[str]:
            """
            Генерация общей информации о модуле.

            Args:
                file_path: Путь к файлу модуля

            Returns:
                Обзор модуля или None при ошибке
            """
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                overview = {
                    'classes': [],
                    'functions': [],
                    'imports': []
                }

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        overview['classes'].append(node.name)
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        overview['functions'].append(node.name)
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        overview['imports'].append(ast.unparse(node))

                return self._format_overview(overview, file_path.name)
            except Exception as e:
                self.logger.error(f"Ошибка генерации обзора модуля: {e}")
                return None

        def _format_overview(self, overview: Dict[str, List], module_name: str) -> str:
            """Форматирование обзора модуля."""
            return f"""# Обзор модуля {module_name}
        Импорты
        {chr(10).join(f'- {imp}' for imp in overview['imports'])}

        Классы
        {chr(10).join(f'- {cls}' for cls in overview['classes'])}

        Функции
        {chr(10).join(f'- {func}' for func in overview['functions'])}
        """