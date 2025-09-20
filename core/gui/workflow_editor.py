"""
Визуальный редактор workflow для AI-ассистента Лиза.
"""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QToolBar, QSplitter, QStatusBar,
                             QFileDialog, QMessageBox, QLabel, QListWidget,
                             QListWidgetItem, QGraphicsView, QGraphicsScene,
                             QMenu, QDialog, QDialogButtonBox, QFormLayout,
                             QLineEdit, QTextEdit, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QSize, QEvent
from PyQt6.QtGui import (QPainter, QColor, QBrush, QPen, QFont, QIcon,
                         QKeyEvent, QMouseEvent, QWheelEvent, QTransform,
                         QActionEvent, QAction)

# Импортируем классы Connection и ConnectionPoint
from core.gui.connection import Connection
from core.gui.connection_point import ConnectionPoint

# Импортируем классы узлов
from core.gui.nodes.base_node import BaseNode
from core.gui.nodes.command_node import CommandNode
from core.gui.nodes.condition_node import ConditionNode
from core.gui.nodes.loop_node import LoopNode


class WorkflowEditor(QMainWindow):
    """Визуальный редактор workflow с drag-and-drop интерфейсом."""

    # Сигналы редактора
    workflow_saved = pyqtSignal(str)  # Идентификатор сохраненного workflow
    workflow_loaded = pyqtSignal(str)  # Идентификатор загруженного workflow
    workflow_changed = pyqtSignal()    # Изменение workflow
    node_selected = pyqtSignal(object) # Выбор ноды

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)

        self.setWindowTitle("Редактор Workflow - Лиза v1.0")
        self.setGeometry(200, 200, 1400, 900)

        self.current_file = None
        self.nodes = []
        self.connections = []
        self.selected_nodes = set()
        self.selected_connection = None
        self.connecting = False
        self.connection_start = None
        self.connection_temp_line = None
        self.zoom_factor = 1.0
        self.grid_size = 20

        self._setup_ui()
        self._setup_toolbar()
        self._setup_shortcuts()

    def _setup_ui(self):
        """Настройка пользовательского интерфейса редактора."""
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QVBoxLayout(central_widget)

        # Splitter для разделения панели инструментов и рабочей области
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Панель инструментов (ноды)
        self.toolbox_widget = self._create_toolbox()
        splitter.addWidget(self.toolbox_widget)

        # Рабочая область
        self.workspace_widget = self._create_workspace()
        splitter.addWidget(self.workspace_widget)

        # Настройка пропорций
        splitter.setSizes([200, 1200])

        main_layout.addWidget(splitter)

        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов")

    def _create_toolbox(self) -> QWidget:
        """Создание панели инструментов с доступными нодами."""
        toolbox = QWidget()
        toolbox.setFixedWidth(200)
        layout = QVBoxLayout(toolbox)

        # Заголовок
        title = QLabel("Доступные ноды")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Список доступных нод
        self.node_list = QListWidget()
        self.node_list.setIconSize(QSize(32, 32))

        # Добавление типов нод
        node_types = [
            ("Команда", "command", ":/icons/command.png"),
            ("Условие", "condition", ":/icons/condition.png"),
            ("Цикл", "loop", ":/icons/loop.png"),
            ("Ввод", "input", ":/icons/input.png"),
            ("Вывод", "output", ":/icons/output.png"),
            ("Задержка", "delay", ":/icons/delay.png")
        ]

        for name, node_type, icon_path in node_types:
            item = QListWidgetItem(QIcon(icon_path), name)
            item.setData(Qt.ItemDataRole.UserRole, node_type)
            self.node_list.addItem(item)

        self.node_list.itemDoubleClicked.connect(self._handle_node_double_click)
        layout.addWidget(self.node_list)

        return toolbox

    def _create_workspace(self) -> QWidget:
        """Создание рабочей области для редактирования workflow."""
        # Создаем графическую сцену
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-1000, -1000, 2000, 2000)
        self.scene.selectionChanged.connect(self._handle_selection_changed)

        # Создаем графическое представление
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Устанавливаем обработчики событий
        self.view.setMouseTracking(True)
        self.view.viewport().installEventFilter(self)

        # Включаем прием событий drag and drop
        self.view.setAcceptDrops(True)

        return self.view

    def _setup_toolbar(self):
        """Настройка панели инструментов редактора."""
        toolbar = QToolBar("Основные инструменты")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Действия
        new_action = QAction(QIcon(":/icons/new.png"), "Новый", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_workflow)
        toolbar.addAction(new_action)

        open_action = QAction(QIcon(":/icons/open.png"), "Открыть", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_workflow)
        toolbar.addAction(open_action)

        save_action = QAction(QIcon(":/icons/save.png"), "Сохранить", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_workflow)
        toolbar.addAction(save_action)

        save_as_action = QAction(QIcon(":/icons/save_as.png"), "Сохранить как", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self._save_as_workflow)
        toolbar.addAction(save_as_action)

        toolbar.addSeparator()

        run_action = QAction(QIcon(":/icons/run.png"), "Запустить", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self._run_workflow)
        toolbar.addAction(run_action)

        debug_action = QAction(QIcon(":/icons/debug.png"), "Отладить", self)
        debug_action.setShortcut("F6")
        debug_action.triggered.connect(self._debug_workflow)
        toolbar.addAction(debug_action)

        toolbar.addSeparator()

        undo_action = QAction(QIcon(":/icons/undo.png"), "Отменить", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self._undo)
        toolbar.addAction(undo_action)

        redo_action = QAction(QIcon(":/icons/redo.png"), "Повторить", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self._redo)
        toolbar.addAction(redo_action)

        toolbar.addSeparator()

        zoom_in_action = QAction(QIcon(":/icons/zoom_in.png"), "Увеличить", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self._zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction(QIcon(":/icons/zoom_out.png"), "Уменьшить", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self._zoom_out)
        toolbar.addAction(zoom_out_action)

        zoom_reset_action = QAction(QIcon(":/icons/zoom_reset.png"), "Сбросить масштаб", self)
        zoom_reset_action.setShortcut("Ctrl+0")
        zoom_reset_action.triggered.connect(self._zoom_reset)
        toolbar.addAction(zoom_reset_action)

        toolbar.addSeparator()

        delete_action = QAction(QIcon(":/icons/delete.png"), "Удалить", self)
        delete_action.setShortcut("Del")
        delete_action.triggered.connect(self._delete_selected)
        toolbar.addAction(delete_action)

    def _setup_shortcuts(self):
        """Настройка горячих клавиш."""
        # Уже настроены в toolbar, но можно добавить дополнительные здесь
        pass

    def eventFilter(self, source, event):
        """Обработка событий мыши для создания соединений."""
        if source is self.view.viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                return self._handle_mouse_press(event)
            elif event.type() == QEvent.Type.MouseMove:
                return self._handle_mouse_move(event)
            elif event.type() == QEvent.Type.MouseButtonRelease:
                return self._handle_mouse_release(event)
            elif event.type() == QEvent.Type.Wheel:
                return self._handle_wheel(event)

        return super().eventFilter(source, event)

    def _handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Обработка нажатия кнопки мыши."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Проверяем, не нажали ли мы на точку соединения
            scene_pos = self.view.mapToScene(event.pos())
            items = self.scene.items(scene_pos)

            for item in items:
                if isinstance(item, ConnectionPoint):
                    self.connecting = True
                    self.connection_start = item

                    # Создаем временную линию
                    self.connection_temp_line = self.scene.addLine(
                        item.scenePos().x(), item.scenePos().y(),
                        scene_pos.x(), scene_pos.y(),
                        QPen(QColor(0, 0, 255), 2, Qt.PenStyle.DashLine)
                    )
                    return True

        elif event.button() == Qt.MouseButton.RightButton:
            # Показываем контекстное меню
            self._show_context_menu(event.globalPos())
            return True

        return False

    def _handle_mouse_move(self, event: QMouseEvent) -> bool:
        """Обработка движения мыши."""
        if self.connecting and self.connection_temp_line:
            scene_pos = self.view.mapToScene(event.pos())
            start_pos = self.connection_start.scenePos()

            # Обновляем временную линию
            self.connection_temp_line.setLine(
                start_pos.x(), start_pos.y(),
                scene_pos.x(), scene_pos.y()
            )
            return True

        return False

    def _handle_mouse_release(self, event: QMouseEvent) -> bool:
        """Обработка отпускания кнопки мыши."""
        if event.button() == Qt.MouseButton.LeftButton and self.connecting:
            self.connecting = False

            # Удаляем временную линию
            if self.connection_temp_line:
                self.scene.removeItem(self.connection_temp_line)
                self.connection_temp_line = None

            # Проверяем, отпустили ли мы на точке соединения
            scene_pos = self.view.mapToScene(event.pos())
            items = self.scene.items(scene_pos)

            for item in items:
                if (isinstance(item, ConnectionPoint) and
                    item != self.connection_start and
                    item.node != self.connection_start.node and
                    item.is_input != self.connection_start.is_input):

                    # Создаем соединение
                    self._create_connection(self.connection_start, item)
                    return True

            return True

        return False

    def _handle_wheel(self, event: QWheelEvent) -> bool:
        """Обработка колесика мыши для масштабирования."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Масштабирование
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom_in()
            else:
                self._zoom_out()
            return True

        return False

    def _handle_selection_changed(self):
        """Обработка изменения выбора на сцене."""
        selected_items = self.scene.selectedItems()
        self.selected_nodes.clear()

        for item in selected_items:
            if isinstance(item, BaseNode):
                self.selected_nodes.add(item)
            elif isinstance(item, Connection):
                self.selected_connection = item

        # Если выбрана одна нода, испускаем сигнал
        if len(self.selected_nodes) == 1:
            self.node_selected.emit(next(iter(self.selected_nodes)))
        else:
            self.node_selected.emit(None)

    def _handle_node_double_click(self, item: QListWidgetItem):
        """Обработка двойного клика на ноде в панели инструментов."""
        node_type = item.data(Qt.ItemDataRole.UserRole)
        self._create_node(node_type)

    def _show_context_menu(self, pos):
        """Показ контекстного меню."""
        menu = QMenu(self)

        # Добавляем действия в зависимости от выбора
        if self.selected_nodes:
            menu.addAction("Свойства", self._edit_selected_node)
            menu.addAction("Удалить", self._delete_selected)
            menu.addSeparator()

        menu.addAction("Создать ноду", self._show_create_node_menu)

        if self.connections:
            menu.addAction("Удалить все соединения", self._delete_all_connections)

        menu.addAction("Очистить рабочую область", self._clear_workspace)

        menu.exec(pos)

    def _show_create_node_menu(self):
        """Показ меню создания ноды."""
        menu = QMenu(self)

        node_types = [
            ("Команда", "command"),
            ("Условие", "condition"),
            ("Цикл", "loop"),
            ("Ввод", "input"),
            ("Вывод", "output"),
            ("Задержка", "delay")
        ]

        for name, node_type in node_types:
            menu.addAction(name, lambda checked=False, nt=node_type: self._create_node(nt))

        menu.exec(self.cursor().pos())

    def _create_node(self, node_type: str, pos: QPointF = None):
        """Создание новой ноды на сцене."""
        if pos is None:
            # Помещаем ноду в центр видимой области
            view_center = self.view.mapToScene(self.view.viewport().rect().center())
            pos = view_center

        node = self._create_node_by_type(node_type)
        if node:
            node.setPos(pos)
            self.scene.addItem(node)
            self.nodes.append(node)
            self.workflow_changed.emit()

            # Если нода имеет диалог настройки, показываем его
            if hasattr(node, 'edit_dialog'):
                node.edit_dialog()

            return node
        return None

    def _create_connection(self, start_point: ConnectionPoint, end_point: ConnectionPoint):
        """Создание соединения между нодами."""
        # Проверяем, не существует ли уже такое соединение
        for connection in self.connections:
            if (connection.start_point == start_point and
                connection.end_point == end_point):
                return connection

        # Проверяем, можно ли соединить эти точки
        if start_point.is_input == end_point.is_input:
            return None  # Нельзя соединить два входа или два выхода

        # Создаем соединение
        connection = Connection(start_point, end_point)
        self.scene.addItem(connection)
        self.connections.append(connection)
        self.workflow_changed.emit()

        return connection

    def _edit_selected_node(self):
        """Редактирование выбранной ноды."""
        if len(self.selected_nodes) == 1:
            node = next(iter(self.selected_nodes))
            if hasattr(node, 'edit_dialog'):
                node.edit_dialog()

    def _delete_selected(self):
        """Удаление выбранных элементов."""
        # Удаляем выбранные ноды
        for node in list(self.selected_nodes):
            # Удаляем все соединения, связанные с этой нодой
            for connection in list(self.connections):
                if (connection.start_point.node == node or
                    connection.end_point.node == node):
                    self.scene.removeItem(connection)
                    self.connections.remove(connection)

            self.scene.removeItem(node)
            self.nodes.remove(node)

        # Удаляем выбранное соединение
        if self.selected_connection:
            self.scene.removeItem(self.selected_connection)
            self.connections.remove(self.selected_connection)
            self.selected_connection = None

        self.workflow_changed.emit()

    def _delete_all_connections(self):
        """Удаление всех соединений."""
        for connection in list(self.connections):
            self.scene.removeItem(connection)
            self.connections.remove(connection)

        self.workflow_changed.emit()

    def _clear_workspace(self):
        """Очистка рабочей области."""
        if self._check_unsaved_changes():
            for node in list(self.nodes):
                self.scene.removeItem(node)
                self.nodes.remove(node)

            for connection in list(self.connections):
                self.scene.removeItem(connection)
                self.connections.remove(connection)

            self.workflow_changed.emit()

    def _zoom_in(self):
        """Увеличение масштаба."""
        self.zoom_factor *= 1.2
        self.view.setTransform(QTransform().scale(self.zoom_factor, self.zoom_factor))

    def _zoom_out(self):
        """Уменьшение масштаба."""
        self.zoom_factor /= 1.2
        self.view.setTransform(QTransform().scale(self.zoom_factor, self.zoom_factor))

    def _zoom_reset(self):
        """Сброс масштаба."""
        self.zoom_factor = 1.0
        self.view.setTransform(QTransform())

    def _new_workflow(self):
        """Создание нового workflow."""
        if self._check_unsaved_changes():
            self._clear_workspace()
            self.current_file = None
            self.status_bar.showMessage("Создан новый workflow")

    def _open_workflow(self):
        """Открытие существующего workflow."""
        if self._check_unsaved_changes():
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Открыть Workflow", "", "JSON Files (*.json)"
            )

            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Очищаем текущий workflow
                    self._clear_workspace()

                    # Загрузка нод
                    for node_data in data.get('nodes', []):
                        node_type = node_data.get('type')
                        node = self._create_node_by_type(node_type)
                        if node:
                            node.deserialize(node_data)
                            self.scene.addItem(node)
                            self.nodes.append(node)

                    # Загрузка соединений
                    for conn_data in data.get('connections', []):
                        start_node_id = conn_data.get('start_node')
                        end_node_id = conn_data.get('end_node')
                        start_point_idx = conn_data.get('start_point')
                        end_point_idx = conn_data.get('end_point')

                        # Находим ноды и точки соединения
                        start_node = next((n for n in self.nodes if n.id == start_node_id), None)
                        end_node = next((n for n in self.nodes if n.id == end_node_id), None)

                        if start_node and end_node:
                            start_point = start_node.output_points[start_point_idx]
                            end_point = end_node.input_points[end_point_idx]
                            self._create_connection(start_point, end_point)

                    self.current_file = file_path
                    self.status_bar.showMessage(f"Загружен workflow: {file_path}")
                    self.workflow_loaded.emit(file_path)

                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить workflow: {e}")

    def _save_workflow(self):
        """Сохранение workflow."""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self._save_as_workflow()

    def _save_as_workflow(self):
        """Сохранение workflow с выбором файла."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить Workflow", "", "JSON Files (*.json)"
        )

        if file_path:
            self._save_to_file(file_path)
            self.current_file = file_path

    def _save_to_file(self, file_path: str):
        """Сохранение workflow в файл."""
        try:
            data = {
                'nodes': self._serialize_nodes(),
                'connections': self._serialize_connections(),
                'metadata': {
                    'version': '1.0',
                    'created': datetime.now().isoformat(),
                    'modified': datetime.now().isoformat()
                }
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.status_bar.showMessage(f"Workflow сохранен: {file_path}")
            self.workflow_saved.emit(file_path)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить workflow: {e}")

    def _run_workflow(self):
        """Запуск текущего workflow."""
        # Валидация workflow перед запуском
        if not self._validate_workflow():
            QMessageBox.warning(self, "Предупреждение", "Workflow содержит ошибки. Проверьте соединения.")
            return

        self.status_bar.showMessage("Запуск workflow...")

        # TODO: Реализовать выполнение workflow
        # Создаем граф выполнения и запускаем его

        # Временная реализация - просто показываем сообщение
        QMessageBox.information(self, "Запуск", "Workflow запущен на выполнение")

    def _debug_workflow(self):
        """Пошаговое выполнение workflow."""
        self.status_bar.showMessage("Отладка workflow...")
        # TODO: Реализовать отладку workflow

        # Временная реализация - просто показываем сообщение
        QMessageBox.information(self, "Отладка", "Режим отладки активирован")

    def _undo(self):
        """Отмена последнего действия."""
        # TODO: Реализовать систему отмены действий
        self.status_bar.showMessage("Отмена последнего действия...")

    def _redo(self):
        """Повтор последнего отмененного действия."""
        # TODO: Реализовать систему повтора действий
        self.status_bar.showMessage("Повтор последнего действия...")

    def _validate_workflow(self) -> bool:
        """Проверка валидности workflow."""
        # Проверяем, что все ноды правильно соединены
        errors = []

        # Проверяем входные ноды (должны иметь соединения на выходе)
        for node in self.nodes:
            if hasattr(node, 'validate') and callable(node.validate):
                node_errors = node.validate()
                if node_errors:
                    errors.extend(node_errors)

        # Проверяем соединения (не должно быть циклов в некоторых случаях)
        # TODO: Реализовать проверку циклов и других ошибок соединений

        # Если есть ошибки, показываем их
        if errors:
            error_msg = "\n".join(errors)
            QMessageBox.warning(self, "Ошибки валидации", f"Найдены ошибки:\n{error_msg}")
            return False

        return True

    def _check_unsaved_changes(self) -> bool:
        """Проверка наличия несохраненных изменений."""
        # TODO: Реализовать проверку изменений
        # Временная реализация - всегда спрашиваем подтверждение
        if self.nodes or self.connections:
            reply = QMessageBox.question(
                self, "Подтверждение",
                "Есть несохраненные изменения. Продолжить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes
        return True

    def _load_nodes(self, nodes_data: List[Dict]) -> List[BaseNode]:
        """Загрузка нод из данных."""
        nodes = []
        for node_data in nodes_data:
            node_type = node_data.get('type')
            node = self._create_node_by_type(node_type)
            if node:
                node.deserialize(node_data)
                nodes.append(node)
        return nodes

    def _create_node_by_type(self, node_type: str) -> Optional[BaseNode]:
        """Создание ноды по типу."""
        if node_type == 'command':
            return CommandNode()
        elif node_type == 'condition':
            return ConditionNode()
        elif node_type == 'loop':
            return LoopNode()
        else:
            self.logger.warning(f"Неизвестный тип ноды: {node_type}")
            return None

    def _serialize_nodes(self) -> List[Dict]:
        """Сериализация нод в данные."""
        return [node.serialize() for node in self.nodes]

    def _serialize_connections(self) -> List[Dict]:
        """Сериализация соединений в данные."""
        connections_data = []

        for connection in self.connections:
            conn_data = {
                'start_node': connection.start_point.node.id,
                'start_point': connection.start_point.node.output_points.index(connection.start_point),
                'end_node': connection.end_point.node.id,
                'end_point': connection.end_point.node.input_points.index(connection.end_point)
            }
            connections_data.append(conn_data)

        return connections_data

    def closeEvent(self, event):
        """Обработка события закрытия окна."""
        if self._check_unsaved_changes():
            event.accept()
        else:
            event.ignore()


# Диалог редактирования свойств ноды
class NodeEditDialog(QDialog):
    """Диалог редактирования свойств ноды."""

    def __init__(self, node, parent=None):
        super().__init__(parent)
        self.node = node
        self.setWindowTitle("Свойства ноды")
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self):
        """Настройка интерфейса диалога."""
        layout = QFormLayout(self)

        # Поле имени
        self.name_edit = QLineEdit(self.node.name)
        layout.addRow("Название:", self.name_edit)

        # Поле описания
        self.desc_edit = QTextEdit(self.node.description)
        layout.addRow("Описание:", self.desc_edit)

        # Дополнительные поля в зависимости от типа ноды
        if hasattr(self.node, 'command'):
            self.command_edit = QLineEdit(self.node.command)
            layout.addRow("Команда:", self.command_edit)

        if hasattr(self.node, 'condition'):
            self.condition_edit = QLineEdit(self.node.condition)
            layout.addRow("Условие:", self.condition_edit)

        if hasattr(self.node, 'loop_count'):
            self.loop_edit = QLineEdit(str(self.node.loop_count))
            layout.addRow("Количество итераций:", self.loop_edit)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept(self):
        """Обработка принятия изменений."""
        self.node.name = self.name_edit.text()
        self.node.description = self.desc_edit.toPlainText()

        if hasattr(self, 'command_edit'):
            self.node.command = self.command_edit.text()

        if hasattr(self, 'condition_edit'):
            self.node.condition = self.condition_edit.text()

        if hasattr(self, 'loop_edit'):
            try:
                self.node.loop_count = int(self.loop_edit.text())
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Количество итераций должно быть числом")
                return

        super().accept()