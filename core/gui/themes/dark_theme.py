"""
Темная тема оформления для графического интерфейса.
"""

from typing import Dict, Any
from PyQt6.QtWidgets import QApplication


class DarkTheme:
    """Темная тема оформления."""

    def __init__(self):
        self.name = "dark"
        self.styles = self._get_styles()

    def _get_styles(self) -> Dict[str, str]:
        """Получение стилей для темной темы."""
        return {
            "application": """
                QMainWindow, QWidget {
                    background-color: #2b2b2b;
                    color: #cccccc;
                }
                QToolBar {
                    background-color: #3c3c3c;
                    border: none;
                    padding: 5px;
                }
                QToolButton {
                    background-color: #3c3c3c;
                    color: #cccccc;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 5px;
                }
                QToolButton:hover {
                    background-color: #4c4c4c;
                }
                QToolButton:pressed {
                    background-color: #5c5c5c;
                }
                QStatusBar {
                    background-color: #3c3c3c;
                    color: #cccccc;
                    border-top: 1px solid #555555;
                }
                QMenuBar {
                    background-color: #3c3c3c;
                    color: #cccccc;
                }
                QMenuBar::item:selected {
                    background-color: #4c4c4c;
                }
                QMenu {
                    background-color: #3c3c3c;
                    color: #cccccc;
                    border: 1px solid #555555;
                }
                QMenu::item:selected {
                    background-color: #4c4c4c;
                }
                QPushButton {
                    background-color: #3c3c3c;
                    color: #cccccc;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #4c4c4c;
                }
                QPushButton:pressed {
                    background-color: #5c5c5c;
                }
                QPushButton:disabled {
                    background-color: #2c2c2c;
                    color: #777777;
                }
                QTextEdit {
                    background-color: #2b2b2b;
                    color: #cccccc;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    selection-background-color: #4c4c4c;
                }
                QListView {
                    background-color: #2b2b2b;
                    color: #cccccc;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    outline: 0;
                }
                QListView::item:selected {
                    background-color: #4c4c4c;
                }
                QListView::item:hover {
                    background-color: #3c3c3c;
                }
                QTabWidget::pane {
                    border: 1px solid #555555;
                    background: #3c3c3c;
                }
                QTabBar::tab {
                    background: #3c3c3c;
                    color: #cccccc;
                    padding: 8px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #2b2b2b;
                    border-bottom: 2px solid #cccccc;
                }
                QListWidget {
                    background-color: #2b2b2b;
                    color: #cccccc;
                    border: 1px solid #555555;
                    border-radius: 4px;
                }
                QListWidget::item:selected {
                    background-color: #4c4c4c;
                }
                QLineEdit {
                    background-color: #2b2b2b;
                    color: #cccccc;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 5px;
                }
                QComboBox {
                    background-color: #2b2b2b;
                    color: #cccccc;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 5px;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 20px;
                    border-left-width: 1px;
                    border-left-color: #555555;
                    border-left-style: solid;
                }
                QCheckBox {
                    color: #cccccc;
                }
                QSpinBox {
                    background-color: #2b2b2b;
                    color: #cccccc;
                    border: 1px solid #555555;
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
            'background': '#2b2b2b',
            'foreground': '#cccccc',
            'accent': '#4c4c4c',
            'border': '#555555',
            'selection': '#4c4c4c',
            'highlight': '#6c6c6c',
            'error': '#ff5555',
            'warning': '#ffb86c',
            'success': '#50fa7b'
        }
        return colors.get(color_name, '#cccccc')