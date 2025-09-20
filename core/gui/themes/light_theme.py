"""
Светлая тема оформления для графического интерфейса.
"""

from typing import Dict, Any
from PyQt6.QtWidgets import QApplication


class LightTheme:
    """Светлая тема оформления."""

    def __init__(self):
        self.name = "light"
        self.styles = self._get_styles()

    def _get_styles(self) -> Dict[str, str]:
        """Получение стилей для светлой темы."""
        return {
            "application": """
                QMainWindow, QWidget {
                    background-color: #ffffff;
                    color: #333333;
                }
                QToolBar {
                    background-color: #f0f0f0;
                    border: none;
                    padding: 5px;
                }
                QToolButton {
                    background-color: #f0f0f0;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 5px;
                }
                QToolButton:hover {
                    background-color: #e0e0e0;
                }
                QToolButton:pressed {
                    background-color: #d0d0d0;
                }
                QStatusBar {
                    background-color: #f0f0f0;
                    color: #333333;
                    border-top: 1px solid #cccccc;
                }
                QMenuBar {
                    background-color: #f0f0f0;
                    color: #333333;
                }
                QMenuBar::item:selected {
                    background-color: #e0e0e0;
                }
                QMenu {
                    background-color: #f0f0f0;
                    color: #333333;
                    border: 1px solid #cccccc;
                }
                QMenu::item:selected {
                    background-color: #e0e0e0;
                }
                QPushButton {
                    background-color: #f0f0f0;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
                QPushButton:disabled {
                    background-color: #f8f8f8;
                    color: #999999;
                }
                QTextEdit {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    selection-background-color: #e0e0e0;
                }
                QListView {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    outline: 0;
                }
                QListView::item:selected {
                    background-color: #e0e0e0;
                }
                QListView::item:hover {
                    background-color: #f0f0f0;
                }
                QTabWidget::pane {
                    border: 1px solid #cccccc;
                    background: #f0f0f0;
                }
                QTabBar::tab {
                    background: #f0f0f0;
                    color: #333333;
                    padding: 8px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #ffffff;
                    border-bottom: 2px solid #333333;
                }
                QListWidget {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                }
                QListWidget::item:selected {
                    background-color: #e0e0e0;
                }
                QLineEdit {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 5px;
                }
                QComboBox {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 5px;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 20px;
                    border-left-width: 1px;
                    border-left-color: #cccccc;
                    border-left-style: solid;
                }
                QCheckBox {
                    color: #333333;
                }
                QSpinBox {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 5px;
                }
            """
        }

    def apply_to_app(self, app: QApplication):
        """Применение темы ко всему приложению."""
        if "application" in self.styles:
            app.setStyleSheet(self.styles["application"])

    def apply_to_widget(self, widget, widget_type: str):
        """Применение темы к конкретному виджету."""
        if widget_type in self.styles:
            widget.setStyleSheet(self.styles[widget_type])

    def get_color(self, color_name: str) -> str:
        """Получение цвета по имени."""
        colors = {
            'background': '#ffffff',
            'foreground': '#333333',
            'accent': '#e0e0e0',
            'border': '#cccccc',
            'selection': '#e0e0e0',
            'highlight': '#d0d0d0',
            'error': '#ff3333',
            'warning': '#ff9900',
            'success': '#33cc33'
        }
        return colors.get(color_name, '#333333')