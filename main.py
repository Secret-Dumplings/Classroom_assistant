from pathlib import Path

from PySide6.QtCore import (
    QParallelAnimationGroup,
    QRectF,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QRegion
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def get_screen_size() -> tuple[int, int]:
    screen = QApplication.primaryScreen()
    if screen:
        size = screen.size()
        return size.width(), size.height()
    return 0, 0


def load_white_svg(svg_path: str, size: int) -> QLabel:
    renderer = QSvgRenderer(svg_path)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor("white"))
    painter.end()
    label = QLabel()
    label.setPixmap(pixmap)
    label.setFixedSize(size, size)
    label.setStyleSheet("background: transparent;")
    return label


class _GradientWindow(QMainWindow):
    def __init__(self, radius: int = 10):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowOpacity(1) #预留透明
        self._radius = radius
        self._border_width = 8

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        r = self._radius

        fill = QColor(0xab, 0xdc, 0x71)
        fill.setAlpha(223)
        painter.setBrush(fill)
        painter.setPen(QPen(QColor(0x46, 0xa3, 0x62), self._border_width))
        painter.drawRoundedRect(0, 0, w, h, r, r)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), self._radius, self._radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))


class SvgWindow(_GradientWindow):
    def __init__(self, size: int = 80, radius: int = 10):
        super().__init__(radius)
        screen_w, _ = get_screen_size()
        x = (screen_w - size) // 2
        self.setGeometry(x, 0, size, size)

        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)

        svg_path = Path(__file__).parent / "ball.svg"
        icon_size = size - 25
        self.svg_label = load_white_svg(str(svg_path), icon_size)
        self.svg_label.setStyleSheet("background: transparent; opacity: 0.70;")

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.svg_label, 0, Qt.AlignmentFlag.AlignCenter)


class TextWindow(_GradientWindow):
    def __init__(self, width: int = 400, height: int = 40, radius: int = 10):
        super().__init__(radius)
        screen_w, _ = get_screen_size()
        x = (screen_w - width) // 2
        self.setGeometry(x, 0, width, height)

        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(1)

        self.title = QLabel("主标题")
        self.title.setStyleSheet("color: white; font-size: 34px; font-weight: bold;")
        layout.addWidget(self.title)

        self.subtitle = QLabel("副标题")
        self.subtitle.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 12px;")
        layout.addWidget(self.subtitle)


class ButtonWindow(_GradientWindow):
    def __init__(self, width: int = 60, height: int = 30, radius: int = 10):
        super().__init__(radius)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setGeometry(0, 0, width, height)

        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.btn = QPushButton("动画")
        self.btn.setFixedSize(width, height)
        self.btn.setStyleSheet(
            "QPushButton { color: white; background: transparent; border: none; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.15); border-radius: 6px; }"
        )
        self.btn.clicked.connect(self._toggle)
        layout.addWidget(self.btn)

        self._drag_pos = None
        self._visible = True
        self._targets: list[QMainWindow] = []

    def set_targets(self, *windows: QMainWindow):
        self._targets = list(windows)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._drag_pos = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _toggle(self):
        self._visible = not self._visible

        def ease_in_out_back(t: float) -> float:
            c1 = 1.70158
            c2 = c1 * 1.525
            if t < 0.5:
                return (pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2)) / 2
            else:
                return (pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2

        group = QParallelAnimationGroup()
        for win in self._targets:
            x = win.x()
            h = win.height()
            if self._visible:
                start_y, end_y = -h, 0
                win.move(x, start_y)
            else:
                start_y, end_y = 0, -h

            anim = QVariantAnimation()
            anim.setDuration(600)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.valueChanged.connect(
                lambda v, w=win, sx=x, sy=start_y, ey=end_y: w.move(
                    sx, int(sy + (ey - sy) * ease_in_out_back(v))
                )
            )
            group.addAnimation(anim)
        group.start()
        self._anim_group = group


if __name__ == "__main__":
    app = QApplication([])

    svg_size = 80
    text_width = 460
    text_height = svg_size
    gap = 4
    total_w = svg_size + gap + text_width
    screen_w, _ = get_screen_size()
    start_x = (screen_w - total_w) // 2

    svg_win = SvgWindow(size=svg_size)
    svg_win.setGeometry(start_x, 0, svg_size, svg_size)
    svg_win.show()

    text_win = TextWindow(width=text_width, height=text_height)
    text_win.setGeometry(start_x + svg_size + gap, 0, text_width, text_height)
    text_win.show()

    btn_win = ButtonWindow()
    btn_win.set_targets(svg_win, text_win)
    btn_win.show()

    app.exec()