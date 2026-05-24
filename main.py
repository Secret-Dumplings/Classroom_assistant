from pathlib import Path

from PySide6.QtCore import (
    QAbstractAnimation,
    QParallelAnimationGroup,
    QRectF,
    QTimer,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QRegion
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
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
        self.setWindowOpacity(1)
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


class _SvgWindow(_GradientWindow):
    def __init__(self, svg_path: str, size: int = 80, radius: int = 10):
        super().__init__(radius)
        self.setGeometry(0, 0, size, size)

        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)

        icon_size = size - 25
        self.svg_label = load_white_svg(svg_path, icon_size)
        self.svg_label.setStyleSheet("background: transparent; opacity: 0.70;")

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.svg_label, 0, Qt.AlignmentFlag.AlignCenter)


class _TextWindow(_GradientWindow):
    def __init__(self, title: str, subtitle: str, width: int = 460, height: int = 80, radius: int = 10):
        super().__init__(radius)
        self.setGeometry(0, 0, width, height)

        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(1)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: white; font-size: 34px; font-weight: bold;")
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 12px;")
        layout.addWidget(self.subtitle_label)


class TopBarManager:
    """顶部通知栏管理器。

    管理两个窗口：左侧方形 SVG 窗口 + 右侧矩形标题窗口，
    支持从屏幕上方滑入/滑出动画和自动隐藏。

    用法:
        manager = TopBarManager(
            svg_path="icon.svg",
            title="语文课",
            subtitle="王老师 · 3班",
            stay_ms=5000,
        )
        manager.show()
    """

    def __init__(
        self,
        svg_path: str,
        title: str = "",
        subtitle: str = "",
        stay_ms: int = 0,
        svg_size: int = 80,
        text_width: int = 460,
        gap: int = 4,
    ):
        """
        Args:
            svg_path: SVG 图标文件路径
            title: 主标题文字
            subtitle: 副标题文字
            stay_ms: 显示停留时间（毫秒），0 表示不自动隐藏
            svg_size: SVG 窗口边长
            text_width: 文字窗口宽度
            gap: 两窗口间距
        """
        self._stay_ms = stay_ms
        self._stay_timer = QTimer()
        self._stay_timer.setSingleShot(True)
        self._stay_timer.timeout.connect(self.hide)
        self._visible = True
        self._anim_group: QParallelAnimationGroup | None = None

        screen_w, _ = get_screen_size()
        total_w = svg_size + gap + text_width
        start_x = (screen_w - total_w) // 2

        self.svg_win = _SvgWindow(svg_path, size=svg_size)
        self.svg_win.setGeometry(start_x, 0, svg_size, svg_size)

        self.text_win = _TextWindow(title, subtitle, width=text_width, height=svg_size)
        self.text_win.setGeometry(start_x + svg_size + gap, 0, text_width, svg_size)

        self._windows = [self.svg_win, self.text_win]

    def show(self):
        """滑入显示，若 stay_ms > 0 则开始倒计时自动隐藏。"""
        self._visible = True
        for win in self._windows:
            win.move(win.x(), -win.height())
            win.show()
        self._animate()
        if self._stay_ms > 0:
            self._stay_timer.start(self._stay_ms)

    def hide(self):
        """滑出隐藏。"""
        self._visible = False
        self._stay_timer.stop()
        self._animate(on_finish=lambda: [win.hide() for win in self._windows])

    def toggle(self):
        """切换显示/隐藏状态。"""
        if self._visible:
            self.hide()
        else:
            self.show()

    def _animate(self, on_finish=None):
        if self._anim_group is not None and self._anim_group.state() == QAbstractAnimation.State.Running:
            self._anim_group.stop()

        group = QParallelAnimationGroup()
        for win in self._windows:
            x = win.x()
            h = win.height()
            if self._visible:
                start_y, end_y = -h, 0
            else:
                start_y, end_y = win.y(), -h

            anim = QVariantAnimation()
            anim.setDuration(600)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.valueChanged.connect(
                lambda v, w=win, sx=x, sy=start_y, ey=end_y: w.move(
                    sx, int(sy + (ey - sy) * _ease_in_out_back(v))
                )
            )
            group.addAnimation(anim)
        if on_finish is not None:
            group.finished.connect(on_finish)
        group.start()
        self._anim_group = group


def _ease_in_out_back(t: float) -> float:
    c1 = 1.70158
    c2 = c1 * 1.525
    if t < 0.5:
        return (pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2)) / 2
    else:
        return (pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2


if __name__ == "__main__":
    app = QApplication([])

    # ── 示例 1：基本用法 ──────────────────────────────
    svg_path = str(Path(__file__).parent / "ball.svg")
    notify = TopBarManager(
        svg_path=svg_path,
        title="距离上课还有2分钟",
        subtitle="马上要上课了，请做好准备",
        stay_ms=5000,  # 5 秒后自动滑出
    )
    notify.show()
    app.exec()