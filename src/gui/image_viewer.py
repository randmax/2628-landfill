from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QImage, QPen, QPixmap
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

    def wheelEvent(self, event) -> None:
        """Zoom under mouse wheel."""
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        self.scale(factor, factor)
