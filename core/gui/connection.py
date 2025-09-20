"""
Соединение между узлами workflow.
"""

from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import Qt, QLineF, QPointF
from PyQt6.QtGui import QPen, QColor


class Connection(QGraphicsItem):
    """Соединение между двумя точками соединения узлов."""

    def __init__(self, start_point, end_point):
        super().__init__()
        self.start_point = start_point
        self.end_point = end_point
        self.start_point.connected = True
        self.end_point.connected = True

        # Устанавливаем флаги для взаимодействия
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setZValue(-1)  # Размещаем соединения под узлами

    def boundingRect(self):
        """Возвращает ограничивающий прямоугольник соединения."""
        start_pos = self.start_point.scenePos()
        end_pos = self.end_point.scenePos()

        # Вычисляем ограничивающий прямоугольник
        min_x = min(start_pos.x(), end_pos.x())
        min_y = min(start_pos.y(), end_pos.y())
        max_x = max(start_pos.x(), end_pos.x())
        max_y = max(start_pos.y(), end_pos.y())

        # Добавляем отступ для толщины линии
        padding = 5
        return QRectF(min_x - padding, min_y - padding,
                      max_x - min_x + 2 * padding, max_y - min_y + 2 * padding)

    def paint(self, painter, option, widget):
        """Отрисовка соединения."""
        start_pos = self.start_point.scenePos()
        end_pos = self.end_point.scenePos()

        # Настройка пера в зависимости от состояния
        if self.isSelected():
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine))
        else:
            painter.setPen(QPen(QColor(0, 0, 255), 2))

        # Рисуем линию
        painter.drawLine(QLineF(start_pos, end_pos))

    def update_position(self):
        """Обновление позиции соединения при перемещении узлов."""
        self.prepareGeometryChange()
        self.update()