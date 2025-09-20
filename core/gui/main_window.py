"""
Главное окно приложения Лиза.
"""

import logging
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QPushButton, QLabel, QStatusBar,
                             QSystemTrayIcon, QMenu, QApplication, QTabWidget,
                             QSplitter, QListWidget, QListWidgetItem, QToolBar,
                             QMessageBox, QDialog, QFormLayout, QLineEdit,
                             QComboBox, QCheckBox, QSpinBox, QDialogButtonBox,
                             QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QAction, QFont, QPalette, QColor

from core.gui.workflow_editor import WorkflowEditor
from core.gui.themes import DarkTheme, LightTheme


class MainWindow(QMainWindow):
    """Главное окно приложения Лиза."""

    # Сигналы приложения
    app_started = pyqtSignal()
    app_stopped = pyqtSignal()
    settings_changed = pyqtSignal(dict)

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.workflow_editor = None
        self.current_theme = "light"
        self.is_listening = False

        self.setWindowTitle("AI Ассистент Лиза v1.0")
        self.setGeometry(100, 100, 1400, 900)

        # Загрузка настроек
        self.settings = self._load_settings()

        self._setup_ui()
        self._setup_tray_icon()
        self._apply_theme()
        self._setup_hotkeys()

    def _load_settings(self) -> dict:
        """Загрузка настроек приложения."""
        default_settings = {
            "theme": "light",
            "autostart": False,
            "notifications": True,
            "log_level": "INFO",
            "max_log_lines": 1000,
            "voice_sensitivity": 0.5,
            "hotkeys": {
                "start_listening": "Ctrl+Space",
                "stop_listening": "Ctrl+Shift+Space",
                "show_hide": "Ctrl+Alt+L"
            }
        }

        try:
            # Создаем папку config если ее нет
            os.makedirs("config", exist_ok=True)
            # Попытка загрузки сохраненных настроек
            with open("config/app_settings.json", "r", encoding="utf-8") as f:
                saved_settings = json.load(f)
                # Объединяем с настройками по умолчанию
                default_settings.update(saved_settings)
        except (FileNotFoundError, json.JSONDecodeError):
            self.logger.warning("Не удалось загрузить настройки, используются настройки по умолчанию")

        return default_settings

    def _save_settings(self):
        """Сохранение настроек приложения."""
        try:
            with open("config/app_settings.json", "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            self.logger.info("Настройки сохранены")
            self.settings_changed.emit(self.settings)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения настроек: {e}")

    def _setup_ui(self):
        """Настройка пользовательского интерфейса."""
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QVBoxLayout(central_widget)

        # Создаем разделитель для основного интерфейса
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Панель навигации слева
        self.nav_panel = self._create_navigation_panel()
        splitter.addWidget(self.nav_panel)

        # Основная область с вкладками справа
        self.tab_widget = QTabWidget()
        splitter.addWidget(self.tab_widget)

        # Настройка пропорций разделителя
        splitter.setSizes([200, 1200])

        # Создаем вкладки
        self._create_dashboard_tab()
        self._create_logs_tab()
        self._create_workflows_tab()
        self._create_settings_tab()

        # Панель статуса
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")

        # Создаем тулбар
        self._setup_toolbar()

        # Подключение сигналов от приложения
        if hasattr(self.app, 'voice_command_received'):
            self.app.voice_command_received.connect(self._on_command_received)
        if hasattr(self.app, 'status_changed'):
            self.app.status_changed.connect(self._on_status_changed)

    def _create_navigation_panel(self) -> QWidget:
        """Создание панели навигации."""
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)

        # Заголовок
        title = QLabel("Лиза v1.0")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 16px; margin: 10px;")
        nav_layout.addWidget(title)

        # Список разделов
        self.nav_list = QListWidget()
        nav_items = [
            ("📊 Дашборд", "dashboard"),
            ("📝 Журнал", "logs"),
            ("⚙️ Workflows", "workflows"),
            ("⚙️ Настройки", "settings"),
            ("📚 Справка", "help")
        ]

        for text, data in nav_items:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, data)
            self.nav_list.addItem(item)

        self.nav_list.currentRowChanged.connect(self._on_navigation_changed)
        nav_layout.addWidget(self.nav_list)

        # Кнопка быстрого запуска
        self.quick_action_btn = QPushButton("🎤 Слушать")
        self.quick_action_btn.clicked.connect(self._on_quick_action)
        nav_layout.addWidget(self.quick_action_btn)

        return nav_widget

    def _create_dashboard_tab(self):
        """Создание вкладки дашборда."""
        dashboard_widget = QWidget()
        layout = QVBoxLayout(dashboard_widget)

        # Заголовок
        title = QLabel("Обзор системы")
        title.setStyleSheet("font-weight: bold; font-size: 18px;")
        layout.addWidget(title)

        # Статистика
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)

        stats = [
            ("Выполнено команд", "152", "#4CAF50"),
            ("Активных workflow", "7", "#2196F3"),
            ("Ошибок", "3", "#F44336"),
            ("Время работы", "12:45:32", "#FF9800")
        ]

        for stat_name, stat_value, color in stats:
            stat_widget = QWidget()
            stat_widget.setStyleSheet(f"background-color: {color}; border-radius: 5px; padding: 10px;")
            stat_layout = QVBoxLayout(stat_widget)

            name_label = QLabel(stat_name)
            name_label.setStyleSheet("color: white; font-size: 12px;")
            value_label = QLabel(stat_value)
            value_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")

            stat_layout.addWidget(name_label)
            stat_layout.addWidget(value_label)
            stats_layout.addWidget(stat_widget)

        layout.addWidget(stats_widget)

        # Последние команды
        recent_label = QLabel("Последние команды:")
        layout.addWidget(recent_label)

        self.recent_commands = QTextEdit()
        self.recent_commands.setReadOnly(True)
        self.recent_commands.setMaximumHeight(200)
        layout.addWidget(self.recent_commands)

        self.tab_widget.addTab(dashboard_widget, "📊 Дашборд")

    def _create_logs_tab(self):
        """Создание вкладки журнала."""
        logs_widget = QWidget()
        layout = QVBoxLayout(logs_widget)

        # Панель управления журналом
        log_controls = QHBoxLayout()

        self.clear_logs_btn = QPushButton("Очистить журнал")
        self.clear_logs_btn.clicked.connect(self._clear_logs)
        log_controls.addWidget(self.clear_logs_btn)

        self.save_logs_btn = QPushButton("Сохранить журнал")
        self.save_logs_btn.clicked.connect(self._save_logs)
        log_controls.addWidget(self.save_logs_btn)

        log_level_label = QLabel("Уровень логирования:")
        log_controls.addWidget(log_level_label)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentText(self.settings.get("log_level", "INFO"))
        self.log_level_combo.currentTextChanged.connect(self._change_log_level)
        log_controls.addWidget(self.log_level_combo)

        layout.addLayout(log_controls)

        # Журнал
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        self.tab_widget.addTab(logs_widget, "📝 Журнал")

    def _create_workflows_tab(self):
        """Создание вкладки workflows."""
        workflows_widget = QWidget()
        layout = QVBoxLayout(workflows_widget)

        # Панель управления workflows
        wf_controls = QHBoxLayout()

        self.new_wf_btn = QPushButton("Создать workflow")
        self.new_wf_btn.clicked.connect(self._create_new_workflow)
        wf_controls.addWidget(self.new_wf_btn)

        self.open_wf_btn = QPushButton("Открыть workflow")
        self.open_wf_btn.clicked.connect(self._open_workflow)
        wf_controls.addWidget(self.open_wf_btn)

        self.run_wf_btn = QPushButton("Запустить выбранный")
        self.run_wf_btn.clicked.connect(self._run_workflow)
        wf_controls.addWidget(self.run_wf_btn)

        layout.addLayout(wf_controls)

        # Список workflows
        wf_list_label = QLabel("Доступные workflows:")
        layout.addWidget(wf_list_label)

        self.wf_list = QListWidget()
        # Загрузка списка workflows из файловой системы
        self._load_workflows_list()
        layout.addWidget(self.wf_list)

        self.tab_widget.addTab(workflows_widget, "⚙️ Workflows")

    def _load_workflows_list(self):
        """Загрузка списка workflows из файловой системы."""
        workflows_dir = "workflows"
        self.wf_list.clear()

        try:
            if not os.path.exists(workflows_dir):
                os.makedirs(workflows_dir)
                self.logger.info(f"Создана директория {workflows_dir}")
                return

            for file in os.listdir(workflows_dir):
                if file.endswith(".json"):
                    workflow_name = file[:-5]  # Убираем расширение .json
                    self.wf_list.addItem(workflow_name)
        except Exception as e:
            self.logger.error(f"Ошибка загрузки списка workflows: {e}")

    def _create_settings_tab(self):
        """Создание вкладки настроек."""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)

        # Форма настроек
        form_layout = QFormLayout()

        # Тема оформления
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Светлая", "Темная"])
        self.theme_combo.setCurrentText("Светлая" if self.settings.get("theme") == "light" else "Темная")
        self.theme_combo.currentTextChanged.connect(self._change_theme)
        form_layout.addRow("Тема оформления:", self.theme_combo)

        # Автозагрузка
        self.autostart_check = QCheckBox()
        self.autostart_check.setChecked(self.settings.get("autostart", False))
        self.autostart_check.stateChanged.connect(self._toggle_autostart)
        form_layout.addRow("Запуск с системой:", self.autostart_check)

        # Уведомления
        self.notifications_check = QCheckBox()
        self.notifications_check.setChecked(self.settings.get("notifications", True))
        self.notifications_check.stateChanged.connect(self._toggle_notifications)
        form_layout.addRow("Показывать уведомления:", self.notifications_check)

        # Чувствительность голоса
        self.voice_sensitivity = QSpinBox()
        self.voice_sensitivity.setRange(1, 100)
        self.voice_sensitivity.setValue(int(self.settings.get("voice_sensitivity", 0.5) * 100))
        self.voice_sensitivity.valueChanged.connect(self._change_voice_sensitivity)
        form_layout.addRow("Чувствительность голоса (%):", self.voice_sensitivity)

        # Максимальное количество строк в журнале
        self.max_log_lines = QSpinBox()
        self.max_log_lines.setRange(100, 10000)
        self.max_log_lines.setValue(self.settings.get("max_log_lines", 1000))
        self.max_log_lines.valueChanged.connect(self._change_max_log_lines)
        form_layout.addRow("Макс. строк в журнале:", self.max_log_lines)

        layout.addLayout(form_layout)

        # Кнопки сохранения/сброса
        button_layout = QHBoxLayout()

        self.save_settings_btn = QPushButton("Сохранить настройки")
        self.save_settings_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(self.save_settings_btn)

        self.reset_settings_btn = QPushButton("Сбросить настройки")
        self.reset_settings_btn.clicked.connect(self._reset_settings)
        button_layout.addWidget(self.reset_settings_btn)

        layout.addLayout(button_layout)

        self.tab_widget.addTab(settings_widget, "⚙️ Настройки")

    def _setup_toolbar(self):
        """Настройка панели инструментов."""
        toolbar = QToolBar("Основная панель")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # Действия
        self.start_action = QAction(QIcon(":/icons/start.png"), "Запуск", self)
        self.start_action.triggered.connect(self._on_start_clicked)
        toolbar.addAction(self.start_action)

        self.stop_action = QAction(QIcon(":/icons/stop.png"), "Остановка", self)
        self.stop_action.triggered.connect(self._on_stop_clicked)
        self.stop_action.setEnabled(False)
        toolbar.addAction(self.stop_action)

        toolbar.addSeparator()

        settings_action = QAction(QIcon(":/icons/settings.png"), "Настройки", self)
        settings_action.triggered.connect(self._show_settings)
        toolbar.addAction(settings_action)

        help_action = QAction(QIcon(":/icons/help.png"), "Справка", self)
        help_action.triggered.connect(self._show_help)
        toolbar.addAction(help_action)

    def _setup_tray_icon(self):
        """Настройка иконки в системном трее."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.logger.warning("Системный трей не доступен")
            return

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(":/icons/app_icon.png"))
        self.tray_icon.setToolTip("AI Ассистент Лиза v1.0")

        # Создание контекстного меню
        tray_menu = QMenu()

        show_action = QAction("Показать", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        hide_action = QAction("Скрыть", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        start_action = QAction("Запустить", self)
        start_action.triggered.connect(self._on_start_clicked)
        tray_menu.addAction(start_action)

        stop_action = QAction("Остановить", self)
        stop_action.triggered.connect(self._on_stop_clicked)
        tray_menu.addAction(stop_action)

        tray_menu.addSeparator()

        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self._on_tray_activated)

        # Показываем уведомление о запуске
        if self.settings.get("notifications", True):
            self.tray_icon.showMessage(
                "Лиза v1.0",
                "Приложение запущено и работает в фоновом режиме",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )

    def _setup_hotkeys(self):
        """Настройка горячих клавиш."""
        # Создаем действия для горячих клавиш
        self.hotkey_actions = {}

        # Горячая клавиша для показа/скрытия окна
        show_hide_action = QAction(self)
        show_hide_action.setShortcut(self.settings["hotkeys"]["show_hide"])
        show_hide_action.triggered.connect(self._toggle_show_hide)
        self.addAction(show_hide_action)
        self.hotkey_actions["show_hide"] = show_hide_action

        # Горячая клавиша для начала прослушивания
        start_listening_action = QAction(self)
        start_listening_action.setShortcut(self.settings["hotkeys"]["start_listening"])
        start_listening_action.triggered.connect(self._start_listening)
        self.addAction(start_listening_action)
        self.hotkey_actions["start_listening"] = start_listening_action

        # Горячая клавиша для остановки прослушивания
        stop_listening_action = QAction(self)
        stop_listening_action.setShortcut(self.settings["hotkeys"]["stop_listening"])
        stop_listening_action.triggered.connect(self._stop_listening)
        self.addAction(stop_listening_action)
        self.hotkey_actions["stop_listening"] = stop_listening_action

    def _apply_theme(self):
        """Применение выбранной темы оформления."""
        if self.settings.get("theme") == "dark":
            theme = LightTheme()
        else:
            theme = DarkTheme()

        theme.apply_to_app(QApplication.instance())

    def _on_tray_activated(self, reason):
        """Обработка активации иконки в трее."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    def _on_navigation_changed(self, index):
        """Обработка изменения выбранного раздела навигации."""
        self.tab_widget.setCurrentIndex(index)

    def _on_quick_action(self):
        """Обработка быстрого действия."""
        # Переключение режима прослушивания
        if not self.is_listening:
            self._start_listening()
        else:
            self._stop_listening()

    def _start_listening(self):
        """Запуск прослушивания."""
        if hasattr(self.app, 'start_listening'):
            self.app.start_listening()
            self.is_listening = True
            self.quick_action_btn.setText("⏹ Остановить")
            self.status_bar.showMessage("Слушаю...")
            self.logger.info("Прослушивание запущено")

    def _stop_listening(self):
        """Остановка прослушивания."""
        if hasattr(self.app, 'stop_listening'):
            self.app.stop_listening()
            self.is_listening = False
            self.quick_action_btn.setText("🎤 Слушать")
            self.status_bar.showMessage("Готов к работе")
            self.logger.info("Прослушивание остановлено")

    def _toggle_show_hide(self):
        """Переключение показа/скрытия окна."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()

    def _on_start_clicked(self):
        """Обработка нажатия кнопки Запуск."""
        self.logger.info("Запуск приложения из GUI")
        self.app_started.emit()

        # Обновление UI
        self.start_action.setEnabled(False)
        self.stop_action.setEnabled(True)

        # Показываем уведомление
        if self.settings.get("notifications", True):
            self.tray_icon.showMessage(
                "Лиза v1.0",
                "Приложение запущено",
                QSystemTrayIcon.MessageIcon.Information,
                1000
            )

    def _on_stop_clicked(self):
        """Обработка нажатия кнопки Остановка."""
        self.logger.info("Остановка приложения из GUI")
        self.app_stopped.emit()

        # Обновление UI
        self.start_action.setEnabled(True)
        self.stop_action.setEnabled(False)

        # Показываем уведомление
        if self.settings.get("notifications", True):
            self.tray_icon.showMessage(
                "Лиза v1.0",
                "Приложение остановлено",
                QSystemTrayIcon.MessageIcon.Information,
                1000
            )

    def _show_settings(self):
        """Показать настройки."""
        self.tab_widget.setCurrentIndex(3)  # Переходим на вкладку настроек
        self.show()
        self.activateWindow()

    def _show_help(self):
        """Показать справку."""
        QMessageBox.information(self, "Справка",
                               "AI Ассистент Лиза v1.0\n\n"
                               "Для получения дополнительной информации посетите:\n"
                               "https://github.com/yourusername/lisa-assistant")

    def _on_command_received(self, command: str):
        """Обработка полученной голосовой команды."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] Команда: {command}")
        self.recent_commands.append(f"[{timestamp}] {command}")

        # Автопрокрутка к новому сообщению
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

        # Ограничение количества строк в журнале
        max_lines = self.settings.get("max_log_lines", 1000)
        if self.log_text.document().lineCount() > max_lines:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def _on_status_changed(self, status: str):
        """Обработка изменения статуса."""
        self.status_bar.showMessage(status)

    def _clear_logs(self):
        """Очистка журнала."""
        self.log_text.clear()
        self.logger.info("Журнал очищен")

    def _save_logs(self):
        """Сохранение журнала в файл."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить журнал", "", "Текстовые файлы (*.txt)"
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.log_text.toPlainText())
                self.logger.info(f"Журнал сохранен в {file_path}")
            except Exception as e:
                self.logger.error(f"Ошибка сохранения журнала: {e}")

    def _change_log_level(self, level):
        """Изменение уровня логирования."""
        self.settings["log_level"] = level
        # Применяем уровень логирования к логгеру
        numeric_level = getattr(logging, level.upper(), None)
        if isinstance(numeric_level, int):
            logging.getLogger().setLevel(numeric_level)
            self.logger.info(f"Уровень логирования изменен на {level}")

    def _create_new_workflow(self):
        """Создание нового workflow."""
        if self.workflow_editor is None:
            self.workflow_editor = WorkflowEditor()
            self.workflow_editor.workflow_saved.connect(self._on_workflow_saved)

        self.workflow_editor.show()
        self.workflow_editor.activateWindow()

    def _open_workflow(self):
        """Открытие существующего workflow."""
        if self.workflow_editor is None:
            self.workflow_editor = WorkflowEditor()
            self.workflow_editor.workflow_saved.connect(self._on_workflow_saved)

        self.workflow_editor._open_workflow()
        self.workflow_editor.show()
        self.workflow_editor.activateWindow()

    def _run_workflow(self):
        """Запуск выбранного workflow."""
        selected_items = self.wf_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Предупреждение", "Выберите workflow для запуска")
            return

        workflow_name = selected_items[0].text()
        self.logger.info(f"Запуск workflow: {workflow_name}")

        # Реализация запуска workflow
        try:
            workflow_path = os.path.join("workflows", f"{workflow_name}.json")
            if hasattr(self.app, 'run_workflow'):
                success = self.app.run_workflow(workflow_path)
                if success:
                    self.status_bar.showMessage(f"Workflow '{workflow_name}' успешно запущен")
                    self.logger.info(f"Workflow '{workflow_name}' успешно запущен")
                else:
                    self.status_bar.showMessage(f"Ошибка запуска workflow '{workflow_name}'")
                    self.logger.error(f"Ошибка запуска workflow '{workflow_name}'")
        except Exception as e:
            self.logger.error(f"Ошибка запуска workflow: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить workflow: {str(e)}")

    def _on_workflow_saved(self, file_path):
        """Обработка сохранения workflow."""
        self.logger.info(f"Workflow сохранен: {file_path}")
        # Обновляем список workflows
        self._load_workflows_list()

    def _change_theme(self, theme_name):
        """Изменение темы оформления."""
        self.settings["theme"] = "light" if theme_name == "Светлая" else "dark"
        self._apply_theme()
        self.logger.info(f"Тема изменена на: {theme_name}")

    def _toggle_autostart(self, state):
        """Переключение автозагрузки."""
        self.settings["autostart"] = state == Qt.CheckState.Checked.value
        self.logger.info(f"Автозагрузка: {'включена' if self.settings['autostart'] else 'выключена'}")

        # Реализация настройки автозагрузки в системе
        try:
            if hasattr(self.app, 'set_autostart'):
                self.app.set_autostart(self.settings["autostart"])
        except Exception as e:
            self.logger.error(f"Ошибка настройки автозагрузки: {e}")

    def _toggle_notifications(self, state):
        """Переключение уведомлений."""
        self.settings["notifications"] = state == Qt.CheckState.Checked.value
        self.logger.info(f"Уведомления: {'включены' if self.settings['notifications'] else 'выключены'}")

    def _change_voice_sensitivity(self, value):
        """Изменение чувствительности голоса."""
        self.settings["voice_sensitivity"] = value / 100.0
        self.logger.info(f"Чувствительность голоса изменена на {value}%")

        # Применяем настройку к системе распознавания голоса
        if hasattr(self.app, 'set_voice_sensitivity'):
            self.app.set_voice_sensitivity(self.settings["voice_sensitivity"])

    def _change_max_log_lines(self, value):
        """Изменение максимального количества строк в журнале."""
        self.settings["max_log_lines"] = value
        self.logger.info(f"Максимальное количество строк в журнале изменено на {value}")

    def _reset_settings(self):
        """Сброс настроек к значениям по умолчанию."""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            default_settings = {
                "theme": "light",
                "autostart": False,
                "notifications": True,
                "log_level": "INFO",
                "max_log_lines": 1000,
                "voice_sensitivity": 0.5
            }

            self.settings = default_settings
            self._apply_theme()
            self._save_settings()

            # Обновляем UI
            self.theme_combo.setCurrentText("Светлая")
            self.autostart_check.setChecked(False)
            self.notifications_check.setChecked(True)
            self.log_level_combo.setCurrentText("INFO")
            self.voice_sensitivity.setValue(50)
            self.max_log_lines.setValue(1000)

            self.logger.info("Настройки сброшены к значениям по умолчанию")

    def closeEvent(self, event):
        """Обработка события закрытия окна."""
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()

            # Показываем уведомление
            if self.settings.get("notifications", True):
                self.tray_icon.showMessage(
                    "Лиза v1.0",
                    "Приложение продолжает работать в фоновом режиме",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
        else:
            # Сохраняем настройки перед выходом
            self._save_settings()
            event.accept()