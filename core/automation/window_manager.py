"""
Модуль управления окнами и приложениями.
"""

import logging
import time
import pygetwindow as gw
import pyautogui
from typing import List, Optional, Tuple

class WindowManager:
    """Менеджер управления окнами и приложениями."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_active_window(self) -> Optional[gw.Window]:
        """Получение активного окна."""
        try:
            return gw.getActiveWindow()
        except Exception as e:
            self.logger.error(f"Ошибка получения активного окна: {e}")
            return None

    def get_all_windows(self) -> List[gw.Window]:
        """Получение всех открытых окон."""
        try:
            return gw.getAllWindows()
        except Exception as e:
            self.logger.error(f"Ошибка получения списка окон: {e}")
            return []

    def find_window(self, title: str) -> Optional[gw.Window]:
        """Поиск окна по заголовку."""
        try:
            windows = gw.getWindowsWithTitle(title)
            return windows[0] if windows else None
        except Exception as e:
            self.logger.error(f"Ошибка поиска окна: {e}")
            return None

    def activate_window(self, window: gw.Window) -> bool:
        """Активация окна."""
        try:
            if window and not window.isActive:
                window.activate()
                time.sleep(0.5)  # Ждем активации
            return True
        except Exception as e:
            self.logger.error(f"Ошибка активации окна: {e}")
            return False

    def maximize_window(self, window: gw.Window) -> bool:
        """Максимизация окна."""
        try:
            if window:
                window.maximize()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка максимизации окна: {e}")
            return False

    def minimize_window(self, window: gw.Window) -> bool:
        """Минимизация окна."""
        try:
            if window:
                window.minimize()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка минимизации окна: {e}")
            return False

    def close_window(self, window: gw.Window) -> bool:
        """Закрытие окна."""
        try:
            if window:
                window.close()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка закрытия окна: {e}")
            return False

    def resize_window(self, window: gw.Window, width: int, height: int) -> bool:
        """Изменение размера окна."""
        try:
            if window:
                window.resizeTo(width, height)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка изменения размера окна: {e}")
            return False

    def move_window(self, window: gw.Window, x: int, y: int) -> bool:
        """Перемещение окна."""
        try:
            if window:
                window.moveTo(x, y)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка перемещения окна: {e}")
            return False

    def get_screen_size(self) -> Tuple[int, int]:
        """Получение размера экрана."""
        try:
            return pyautogui.size()
        except Exception as e:
            self.logger.error(f"Ошибка получения размера экрана: {e}")
            return (1920, 1080)  # Значение по умолчанию

    def take_screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional:
        """Создание скриншота."""
        try:
            return pyautogui.screenshot(region=region)
        except Exception as e:
            self.logger.error(f"Ошибка создания скриншота: {e}")
            return None