"""
Точка соединения для узлов workflow.
"""

from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPen, QBrush, QColor


class ConnectionPoint(QGraphicsItem):
    """Точка соединения для узлов workflow."""

    def __init__(self, node, is_input=True, index=0):
        super().__init__(node)
        self.node = node
        self.is_input = is_input  # True для входной точки, False для выходной
        self.index = index
        self.radius = 5
        self.connected = False

        # Устанавливаем флаги для взаимодействия
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        """Возвращает ограничивающий прямоугольник точки соединения."""
        return QRectF(-self.radius, -self.radius, 2 * self.radius, 2 * self.radius)

    def paint(self, painter, option, widget):
        """Отрисовка точки соединения."""
        # Настройка пера и кисти
        if self.connected:
            painter.setPen(QPen(QColor(0, 100, 0), 1))
            painter.setBrush(QBrush(QColor(0, 200, 0)))
        else:
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.setBrush(QBrush(QColor(200, 200, 200)))

        # Рисуем круг
        painter.drawEllipse(-self.radius, -self.radius, 2 * self.radius, 2 * self.radius)

    def hoverEnterEvent(self, event):
        """Обработка наведения курсора на точку соединения."""
        self.setCursor(Qt.CursorShape.CrossCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Обработка ухода курсора с точки соединения."""
        self.unsetCursor()
        super().hoverLeaveEvent(event)