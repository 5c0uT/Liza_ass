"""
Базовый класс для всех нод в визуальном редакторе.
"""

import logging
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (QPainter, QColor, QBrush, QPen, QFont,
                         QLinearGradient, QPainterPath, QAction)
from PyQt6.QtWidgets import (QGraphicsItem, QWidget, QStyleOptionGraphicsItem,
                             QGraphicsSceneMouseEvent, QMenu, QGraphicsSceneHoverEvent)


class BaseNode(QGraphicsItem):
    """Базовый класс для всех нод в редакторе workflow."""

    def __init__(self, title: str = "Нода", parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)

        self.title = title
        self.inputs = []  # Список входных портов
        self.outputs = []  # Список выходных портов
        self.properties = {}  # Свойства ноды
        self.connections = []  # Список соединений
        self.node_type = self.__class__.__name__  # Тип ноды

        # Настройка внешнего вида
        self.width = 200
        self.min_height = 100
        self.height = self.min_height
        self.radius = 8
        self.header_height = 30
        self.port_size = 12
        self.port_spacing = 25

        # Цвета
        self.header_color = QColor(70, 130, 180)
        self.body_color = QColor(240, 240, 240)
        self.border_color = QColor(50, 50, 50)
        self.text_color = QColor(0, 0, 0)
        self.port_color = QColor(100, 100, 100)
        self.selection_color = QColor(255, 165, 0)

        # Тени и градиенты
        self.shadow_enabled = True
        self.gradient_enabled = True

        # Флаги взаимодействия
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable)
        self.setAcceptHoverEvents(True)

        # Контекстное меню
        self.setup_context_menu()

        # Инициализация свойств по умолчанию
        self.init_properties()

    def boundingRect(self) -> QRectF:
        """Возвращает ограничивающий прямоугольник ноды."""
        return QRectF(0, 0, self.width, self.height).adjusted(-2, -2, 2, 2)

    def shape(self) -> QPainterPath:
        """Возвращает форму ноды для точного определения попадания."""
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width, self.height, self.radius, self.radius)
        return path

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        """Отрисовка ноды."""
        # Настройка рендеринга
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Рисование тени
        if self.shadow_enabled:
            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(2, 2, self.width, self.height, self.radius, self.radius)
            painter.fillPath(shadow_path, QColor(0, 0, 0, 50))

        # Рисование тела ноды с градиентом
        body_rect = QRectF(0, 0, self.width, self.height)
        if self.gradient_enabled:
            gradient = QLinearGradient(0, 0, 0, self.height)
            gradient.setColorAt(0, self.body_color.lighter(110))
            gradient.setColorAt(1, self.body_color.darker(110))
            painter.setBrush(QBrush(gradient))
        else:
            painter.setBrush(QBrush(self.body_color))

        painter.setPen(QPen(self.border_color, 1.5))
        painter.drawRoundedRect(body_rect, self.radius, self.radius)

        # Рисование заголовка с градиентом
        header_rect = QRectF(0, 0, self.width, self.header_height)
        if self.gradient_enabled:
            header_gradient = QLinearGradient(0, 0, 0, self.header_height)
            header_gradient.setColorAt(0, self.header_color.lighter(120))
            header_gradient.setColorAt(1, self.header_color.darker(120))
            painter.setBrush(QBrush(header_gradient))
        else:
            painter.setBrush(QBrush(self.header_color))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(header_rect, self.radius, self.radius)

        # Верхние углы заголовка закруглены, нижние - нет
        painter.drawRect(0, self.header_height - self.radius, self.radius, self.radius)
        painter.drawRect(self.width - self.radius, self.header_height - self.radius,
                        self.radius, self.radius)

        # Рисование текста заголовка
        painter.setPen(QPen(self.text_color))
        font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(header_rect, Qt.AlignmentFlag.AlignCenter, self.title)

        # Рисование входных портов
        for i, port in enumerate(self.inputs):
            y_pos = self.header_height + 15 + i * self.port_spacing
            port_rect = QRectF(5, y_pos - self.port_size/2, self.port_size, self.port_size)

            # Рисование круга порта
            painter.setBrush(QBrush(self.port_color))
            painter.setPen(QPen(self.border_color, 1))
            painter.drawEllipse(port_rect)

            # Рисование текста порта
            painter.setPen(QPen(self.text_color))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(20, y_pos + 4, port['name'])

        # Рисование выходных портов
        for i, port in enumerate(self.outputs):
            y_pos = self.header_height + 15 + i * self.port_spacing
            port_rect = QRectF(self.width - self.port_size - 5,
                              y_pos - self.port_size/2,
                              self.port_size, self.port_size)

            # Рисование круга порта
            painter.setBrush(QBrush(self.port_color))
            painter.setPen(QPen(self.border_color, 1))
            painter.drawEllipse(port_rect)

            # Рисование текста порта
            painter.setPen(QPen(self.text_color))
            painter.setFont(QFont("Arial", 8))
            text_width = painter.fontMetrics().horizontalAdvance(port['name'])
            painter.drawText(self.width - text_width - 25, y_pos + 4, port['name'])

        # Выделение если выбрано
        if self.isSelected():
            painter.setPen(QPen(self.selection_color, 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(body_rect, self.radius, self.radius)

        # Рисование иконки типа ноды (опционально)
        self.paint_icon(painter)

    def paint_icon(self, painter: QPainter):
        """Отрисовка иконки типа ноды в заголовке."""
        # Базовый класс не реализует специфичную иконку
        # Может быть переопределен в наследниках
        pass

    def add_input(self, name: str, data_type: str = "any", multi_connection: bool = False) -> None:
        """Добавление входного порта."""
        self.inputs.append({
            'name': name,
            'type': data_type,
            'multi_connection': multi_connection,
            'position': len(self.inputs)
        })

        # Обновляем высоту ноды при необходимости
        self.update_height()
        self.update()

    def add_output(self, name: str, data_type: str = "any", multi_connection: bool = True) -> None:
        """Добавление выходного порта."""
        self.outputs.append({
            'name': name,
            'type': data_type,
            'multi_connection': multi_connection,
            'position': len(self.outputs)
        })

        # Обновляем высоту ноды при необходимости
        self.update_height()
        self.update()

    def update_height(self):
        """Обновление высоты ноды в зависимости от количества портов."""
        max_ports = max(len(self.inputs), len(self.outputs))
        new_height = self.header_height + 20 + max_ports * self.port_spacing
        self.height = max(self.min_height, new_height)
        self.prepareGeometryChange()

    def set_property(self, name: str, value: Any) -> None:
        """Установка свойства ноды."""
        self.properties[name] = value
        if hasattr(self, 'properties_changed') and self.properties_changed:
            self.properties_changed.emit(self, name, value)

    def get_property(self, name: str, default: Any = None) -> Any:
        """Получение свойства ноды."""
        return self.properties.get(name, default)

    def init_properties(self):
        """Инициализация свойств по умолчанию."""
        # Базовый класс не имеет специфичных свойств
        # Может быть переопределен в наследниках
        pass

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение ноды (должен быть переопределен в подклассах)."""
        raise NotImplementedError("Метод execute должен быть реализован в подклассе")

    def on_connected(self, connection):
        """Обработка события подключения соединения."""
        self.connections.append(connection)
        self.logger.debug(f"К ноде {self.title} подключено соединение")

    def on_disconnected(self, connection):
        """Обработка события отключения соединения."""
        if connection in self.connections:
            self.connections.remove(connection)
        self.logger.debug(f"От ноды {self.title} отключено соединение")

    def get_input_port_rect(self, index: int) -> QRectF:
        """Получение прямоугольника входного порта."""
        if 0 <= index < len(self.inputs):
            y_pos = self.header_height + 15 + index * self.port_spacing
            return QRectF(5, y_pos - self.port_size/2, self.port_size, self.port_size)
        return QRectF()

    def get_output_port_rect(self, index: int) -> QRectF:
        """Получение прямоугольника выходного порта."""
        if 0 <= index < len(self.outputs):
            y_pos = self.header_height + 15 + index * self.port_spacing
            return QRectF(self.width - self.port_size - 5,
                         y_pos - self.port_size/2,
                         self.port_size, self.port_size)
        return QRectF()

    def get_input_port_position(self, index: int) -> QPointF:
        """Получение позиции входного порта."""
        port_rect = self.get_input_port_rect(index)
        return self.mapToScene(port_rect.center())

    def get_output_port_position(self, index: int) -> QPointF:
        """Получение позиции выходного порта."""
        port_rect = self.get_output_port_rect(index)
        return self.mapToScene(port_rect.center())

    def get_port_at_position(self, pos: QPointF) -> Optional[Dict[str, Any]]:
        """Получение порта по позиции."""
        local_pos = self.mapFromScene(pos)

        # Проверяем входные порты
        for i, port in enumerate(self.inputs):
            port_rect = self.get_input_port_rect(i)
            if port_rect.contains(local_pos):
                return {'type': 'input', 'index': i, 'port': port}

        # Проверяем выходные порты
        for i, port in enumerate(self.outputs):
            port_rect = self.get_output_port_rect(i)
            if port_rect.contains(local_pos):
                return {'type': 'output', 'index': i, 'port': port}

        return None

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        """Обработка перемещения ноды."""
        old_pos = self.pos()
        super().mouseMoveEvent(event)

        # Обновление соединений при перемещении
        for connection in self.connections:
            connection.update_path()

        # Отправка сигнала о перемещении
        if hasattr(self, 'node_moved') and self.node_moved and old_pos != self.pos():
            self.node_moved.emit(self, old_pos, self.pos())

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        """Обработка нажатия на ноду."""
        super().mousePressEvent(event)

        # Отправка сигнала о выборе
        if hasattr(self, 'node_selected') and self.node_selected and event.button() == Qt.MouseButton.LeftButton:
            self.node_selected.emit(self)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        """Обработка двойного клика на ноду."""
        super().mouseDoubleClickEvent(event)
        # Можно открыть диалог редактирования свойств
        self.edit_properties()

    def contextMenuEvent(self, event: QGraphicsSceneMouseEvent):
        """Обработка контекстного меню."""
        self.context_menu.exec(event.screenPos())

    def setup_context_menu(self):
        """Настройка контекстного меню ноды."""
        self.context_menu = QMenu()

        # Действия меню
        edit_action = QAction("Редактировать свойства", self.context_menu)
        edit_action.triggered.connect(self.edit_properties)
        self.context_menu.addAction(edit_action)

        delete_action = QAction("Удалить", self.context_menu)
        delete_action.triggered.connect(self.delete_node)
        self.context_menu.addAction(delete_action)

        self.context_menu.addSeparator()

        # Дополнительные действия могут быть добавлены в наследниках
        self.setup_custom_context_menu()

    def setup_custom_context_menu(self):
        """Настройка пользовательского контекстного меню."""
        # Может быть переопределен в наследниках
        pass

    def edit_properties(self):
        """Редактирование свойств ноды."""
        # Базовый класс не реализует редактирование свойств
        # Может быть переопределен в наследниках
        self.logger.info(f"Редактирование свойств ноды: {self.title}")

    def delete_node(self):
        """Удаление ноды."""
        # Отключаем все соединения
        for connection in self.connections[:]:
            connection.delete()

        # Удаляем ноду из сцены
        if self.scene():
            self.scene().removeItem(self)

    def serialize(self) -> Dict[str, Any]:
        """Сериализация ноды в данные."""
        return {
            'type': self.node_type,
            'title': self.title,
            'position': (self.x(), self.y()),
            'inputs': self.inputs,
            'outputs': self.outputs,
            'properties': self.properties,
            'uuid': str(id(self))  # Уникальный идентификатор
        }

    def deserialize(self, data: Dict[str, Any]) -> None:
        """Десериализация ноды из данных."""
        self.title = data.get('title', self.title)
        position = data.get('position', (0, 0))
        self.setPos(*position)
        self.inputs = data.get('inputs', [])
        self.outputs = data.get('outputs', [])
        self.properties = data.get('properties', {})

        # Обновляем высоту после загрузки портов
        self.update_height()
        self.update()

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent):
        """Обработка наведения курсора на ноду."""
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent):
        """Обработка выхода курсора из ноды."""
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    def validate_connections(self) -> List[str]:
        """Проверка корректности соединений ноды."""
        errors = []

        # Проверяем обязательные входы
        for port in self.inputs:
            if port.get('required', False):
                connected = any(conn for conn in self.connections
                               if hasattr(conn, 'input_port') and conn.input_port == port)
                if not connected:
                    errors.append(f"Обязательный вход '{port['name']}' не подключен")

        return errors

    def get_status_color(self) -> QColor:
        """Получение цвета статуса ноды."""
        # Базовый класс возвращает нейтральный цвет
        # Может быть переопределен в наследниках для отображения статуса выполнения
        return QColor(200, 200, 200)

    def update_visuals(self):
        """Обновление визуального представления ноды."""
        self.update()