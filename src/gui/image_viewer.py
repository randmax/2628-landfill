from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsTextItem, QGraphicsView

from src.models.roi_result import RoiResult


class ImageViewer(QGraphicsView):
    """Zoomable graphics view for thermal previews and ROI overlays."""

    def __init__(self) -> None:
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.pixmap_item: QGraphicsPixmapItem | None = None
        self.box_item: QGraphicsRectItem | None = None
        self.label_item: QGraphicsTextItem | None = None
        self.temperature_matrix: np.ndarray | None = None
        self.measurement_items: list[dict[str, object]] = []

    def set_image(self, rgb) -> None:
        """Show an RGB uint8 image."""
        h, w, _ = rgb.shape
        image = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(image)
        self.scene.clear()
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(QRectF(0, 0, w, h))
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.box_item = None
        self.label_item = None
        self.measurement_items = []

    def set_roi(self, roi: RoiResult | None, show_box: bool = True, show_label: bool = True) -> None:
        """Draw or clear the ROI overlay."""
        if self.box_item:
            self.scene.removeItem(self.box_item)
        if self.label_item:
            self.scene.removeItem(self.label_item)
        self.box_item = None
        self.label_item = None
        if roi is None:
            return
        if show_box:
            pen = QPen(Qt.yellow)
            pen.setWidth(2)
            self.box_item = self.scene.addRect(roi.x, roi.y, roi.width, roi.height, pen)
        if show_label:
            text = f"ROI átlag: {roi.mean_temperature:.1f} °C\nROI max: {roi.max_temperature:.1f} °C\nP95: {roi.p95_temperature:.1f} °C"
            self.label_item = self.scene.addText(text)
            self.label_item.setDefaultTextColor(Qt.black)
            self.label_item.setPos(QPointF(roi.x, max(0, roi.y - 48)))
            self.label_item.setTextInteractionFlags(Qt.NoTextInteraction)

    def set_roi_preview(self, width: int, height: int, label: str) -> None:
        """Draw an active ROI preview centered on the displayed image."""
        if self.box_item:
            self.scene.removeItem(self.box_item)
        if self.label_item:
            self.scene.removeItem(self.label_item)
        self.box_item = None
        self.label_item = None
        rect = self.scene.sceneRect()
        if rect.isEmpty():
            return
        w = max(1, min(width, int(rect.width())))
        h = max(1, min(height, int(rect.height())))
        x = (rect.width() - w) / 2.0
        y = (rect.height() - h) / 2.0
        pen = QPen(Qt.cyan)
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        self.box_item = self.scene.addRect(x, y, w, h, pen)
        self.label_item = self.scene.addText(label)
        self.label_item.setDefaultTextColor(Qt.black)
        self.label_item.setPos(QPointF(x, max(0, y - 28)))

    def set_temperature_matrix(self, matrix: np.ndarray | None) -> None:
        """Beállítja a kattintható hőmérsékleti mintavétel forrását."""
        self.temperature_matrix = matrix
        if matrix is not None:
            self.setDragMode(QGraphicsView.NoDrag)
            self.viewport().setCursor(Qt.CrossCursor)
        else:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.viewport().setCursor(Qt.ArrowCursor)
        self.clear_measurements()

    def clear_measurements(self) -> None:
        """Eltávolítja a képre kattintott hőmérsékleti pontokat."""
        for measurement in self.measurement_items:
            for item in measurement["items"]:
                self.scene.removeItem(item)
        self.measurement_items = []

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._add_temperature_measurement(event):
            return
        if event.button() == Qt.RightButton and self._remove_nearest_measurement(event):
            return
        super().mousePressEvent(event)

    def _add_temperature_measurement(self, event) -> bool:
        if self.temperature_matrix is None:
            return False
        point = self.mapToScene(event.position().toPoint())
        x = int(round(point.x()))
        y = int(round(point.y()))
        height, width = self.temperature_matrix.shape[:2]
        if x < 0 or y < 0 or x >= width or y >= height:
            return False
        temperature = float(self.temperature_matrix[y, x])
        if not math.isfinite(temperature):
            return False

        marker_pen = QPen(Qt.red)
        marker_pen.setWidth(2)
        marker_brush = QBrush(Qt.red)
        marker = self.scene.addEllipse(x - 4, y - 4, 8, 8, marker_pen, marker_brush)
        label = self.scene.addText(f"{temperature:.1f} °C\n({x}, {y})")
        label.setFont(QFont("Arial", 8))
        label.setDefaultTextColor(Qt.black)
        label_pos = QPointF(x + 8, y - 28)
        label.setPos(label_pos)
        label_rect = label.mapToScene(label.boundingRect()).boundingRect().adjusted(-4, -3, 4, 3)
        background = self.scene.addRect(
            label_rect,
            QPen(QColor(17, 24, 39)),
            QBrush(QColor(255, 255, 255, 225)),
        )
        background.setZValue(9)
        marker.setZValue(10)
        label.setZValue(11)
        self.measurement_items.append({"point": QPointF(x, y), "items": [marker, background, label]})
        return True

    def _remove_nearest_measurement(self, event) -> bool:
        if not self.measurement_items:
            return False
        point = self.mapToScene(event.position().toPoint())
        nearest_index = -1
        nearest_distance = float("inf")
        for index, measurement in enumerate(self.measurement_items):
            measured_point = measurement["point"]
            distance = math.hypot(point.x() - measured_point.x(), point.y() - measured_point.y())
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_index = index
        if nearest_index < 0 or nearest_distance > 24:
            return False
        measurement = self.measurement_items.pop(nearest_index)
        for item in measurement["items"]:
            self.scene.removeItem(item)
        return True

    def wheelEvent(self, event) -> None:
        """Zoom under mouse wheel."""
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        self.scale(factor, factor)
