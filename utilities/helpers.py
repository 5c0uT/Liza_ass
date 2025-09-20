"""
Вспомогательные функции для приложения Лиза.
"""

import inspect
import json
import yaml
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path


def load_config(config_path: Path) -> Optional[Dict[str, Any]]:
    """
    Загрузка конфигурации из файла.

    Поддерживаемые форматы: JSON, YAML, TOML
    """
    if not config_path.exists():
        return None

    try:
        suffix = config_path.suffix.lower()

        if suffix == '.json':
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        elif suffix in ['.yaml', '.yml']:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)

        elif suffix == '.toml':
            import toml
            with open(config_path, 'r', encoding='utf-8') as f:
                return toml.load(f)

        else:
            raise ValueError(f"Неподдерживаемый формат конфигурации: {suffix}")

    except Exception as e:
        print(f"Ошибка загрузки конфигурации {config_path}: {e}")
        return None


def save_config(config_path: Path, config: Dict[str, Any]) -> bool:
    """
    Сохранение конфигурации в файл.

    Поддерживаемые форматы: JSON, YAML, TOML
    """
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        suffix = config_path.suffix.lower()

        if suffix == '.json':
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

        elif suffix in ['.yaml', '.yml']:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True)

        elif suffix == '.toml':
            import toml
            with open(config_path, 'w', encoding='utf-8') as f:
                toml.dump(config, f)

        else:
            raise ValueError(f"Неподдерживаемый формат конфигурации: {suffix}")

        return True

    except Exception as e:
        print(f"Ошибка сохранения конфигурации {config_path}: {e}")
        return False


def get_function_parameters(func: Callable) -> List[str]:
    """Получение списка параметров функции."""
    try:
        signature = inspect.signature(func)
        return list(signature.parameters.keys())
    except:
        return []


def validate_config(config: Dict[str, Any], required_fields: List[str]) -> bool:
    """Проверка наличия обязательных полей в конфигурации."""
    for field in required_fields:
        if field not in config:
            return False
    return True


def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """Рекурсивное слияние двух словарей."""
    result = dict1.copy()

    for key, value in dict2.items():
        if (key in result and isinstance(result[key], dict)
                and isinstance(value, dict)):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result