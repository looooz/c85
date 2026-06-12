from datetime import datetime
from PyQt6.QtWidgets import (
    QSystemTrayIcon, QMenu, QApplication, QWidget,
    QVBoxLayout, QLabel, QHBoxLayout,
)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QIcon, QAction, QPainter, QColor, QFont, QPixmap

import database
from core import ReminderEngine, FocusModeManager
from theme import get_theme_manager


def create_tray_icon(icon_char="⏰", size=64):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#e94560"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, size - 4, size - 4)
    painter.setPen(QColor("#ffffff"))
    font = QFont()
    font.setPointSize(int(size * 0.5))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, icon_char)
    painter.end()
    return QIcon(pixmap)


class FloatingWindow(QWidget):
    def __init__(self, engine: ReminderEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.theme_manager = get_theme_manager(self)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._init_ui()
        self._drag_pos = None
        self._start_timer()
        self.theme_manager.theme_changed.connect(self._apply_theme)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        self.inner_widget = QWidget()
        self.inner_widget.setObjectName("floatingInner")
        inner_layout = QVBoxLayout(self.inner_widget)
        inner_layout.setContentsMargins(10, 8, 10, 8)

        self.title_label = QLabel("下一个提醒")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner_layout.addWidget(self.title_label)

        self.time_label = QLabel("--:--")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner_layout.addWidget(self.time_label)

        self.content_label = QLabel("暂无")
        self.content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner_layout.addWidget(self.content_label)

        layout.addWidget(self.inner_widget)
        self.resize(160, 90)
        self._apply_theme()

    def _apply_theme(self):
        theme = self.theme_manager.get_theme()
        name = theme["name"]
        if name == "dark":
            bg = "rgba(26, 26, 46, 230)"
        else:
            bg = "rgba(255, 255, 255, 230)"
        self.inner_widget.setStyleSheet(f"""
            #floatingInner {{
                background: {bg};
                border: 1px solid {theme['border_accent']};
                border-radius: 10px;
            }}
        """)
        self.title_label.setStyleSheet(f"color: {theme['text_accent']}; font-size: 11px; font-weight: bold;")
        self.time_label.setStyleSheet(f"color: {theme['text_primary']}; font-size: 18px; font-weight: bold;")
        self.content_label.setStyleSheet(f"color: {theme['text_secondary']}; font-size: 11px;")

    def _start_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_info)
        self._timer.start(1000)
        self._update_info()

    def _update_info(self):
        r, t = self.engine.get_next_reminder()
        if r and t:
            now = datetime.now()
            delta = t - now
            if delta.total_seconds() > 0:
                hours, remainder = divmod(int(delta.total_seconds()), 3600)
                mins, secs = divmod(remainder, 60)
                if hours > 0:
                    self.time_label.setText(f"{hours:02d}:{mins:02d}:{secs:02d}")
                else:
                    self.time_label.setText(f"{mins:02d}:{secs:02d}")
                self.content_label.setText(r["title"])
            else:
                self.time_label.setText("即将触发")
                self.content_label.setText(r["title"])
        else:
            self.time_label.setText("--:--")
            self.content_label.setText("暂无提醒")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


class TrayManager:
    def __init__(self, main_window, engine: ReminderEngine, focus_mode: FocusModeManager):
        self.main_window = main_window
        self.engine = engine
        self.focus_mode = focus_mode
        self.floating_window = None

        self.tray = QSystemTrayIcon(main_window)
        self.tray.setIcon(create_tray_icon())
        self.tray.setToolTip("多功能提醒工具")

        self.menu = QMenu()
        self._build_menu()

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_activated)
        self.tray.show()

        self._update_menu_states()
        self._start_menu_timer()

    def _build_menu(self):
        self.menu.clear()

        show_action = QAction("📋 显示主窗口", self.menu)
        show_action.triggered.connect(self._show_main_window)
        self.menu.addAction(show_action)

        self.focus_action = QAction("🧘 专注模式", self.menu)
        self.focus_action.setCheckable(True)
        self.focus_action.triggered.connect(self._toggle_focus)
        self.menu.addAction(self.focus_action)

        self.pause_action = QAction("⏸️ 暂停所有提醒", self.menu)
        self.pause_action.setCheckable(True)
        self.pause_action.triggered.connect(self._toggle_pause)
        self.menu.addAction(self.pause_action)

        self.floating_action = QAction("🔲 显示悬浮窗", self.menu)
        self.floating_action.setCheckable(True)
        self.floating_action.triggered.connect(self._toggle_floating)
        self.menu.addAction(self.floating_action)

        self.menu.addSeparator()

        history_action = QAction("📊 历史记录", self.menu)
        history_action.triggered.connect(self._show_history)
        self.menu.addAction(history_action)

        settings_action = QAction("⚙️ 设置", self.menu)
        settings_action.triggered.connect(self._show_settings)
        self.menu.addAction(settings_action)

        self.menu.addSeparator()

        quit_action = QAction("🚪 退出", self.menu)
        quit_action.triggered.connect(self._quit)
        self.menu.addAction(quit_action)

    def _start_menu_timer(self):
        self._menu_timer = QTimer(self.main_window)
        self._menu_timer.timeout.connect(self._update_menu_states)
        self._menu_timer.start(2000)

    def _update_menu_states(self):
        self.focus_action.setChecked(self.focus_mode.enabled)
        self.pause_action.setChecked(self.engine.is_paused())
        self.floating_action.setChecked(self.floating_window is not None and self.floating_window.isVisible())

        if self.focus_mode.enabled:
            self.focus_action.setText("🧘 专注模式（已开启）")
        else:
            self.focus_action.setText("🧘 专注模式")

        if self.engine.is_paused():
            self.pause_action.setText("▶️ 恢复所有提醒")
        else:
            self.pause_action.setText("⏸️ 暂停所有提醒")

        r, t = self.engine.get_next_reminder()
        if r and t:
            delta = t - datetime.now()
            if delta.total_seconds() > 0:
                mins = int(delta.total_seconds() // 60)
                if mins > 0:
                    self.tray.setToolTip(f"多功能提醒工具\n下一个：{r['title']}（{mins}分钟后）")
                else:
                    self.tray.setToolTip(f"多功能提醒工具\n下一个：{r['title']}（即将触发）")
            else:
                self.tray.setToolTip("多功能提醒工具\n即将触发提醒")
        else:
            self.tray.setToolTip("多功能提醒工具\n暂无待触发提醒")

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_main_window()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_main_window()

    def _show_main_window(self):
        self.main_window.showNormal()
        self.main_window.activateWindow()
        self.main_window.raise_()

    def _toggle_focus(self, checked):
        self.focus_mode.set_enabled(checked)
        if hasattr(self.main_window, 'focus_btn'):
            self.main_window.focus_btn.setChecked(checked)
        self._update_menu_states()

    def _toggle_pause(self, checked):
        self.engine.set_paused(checked)
        if hasattr(self.main_window, 'pause_btn'):
            self.main_window.pause_btn.setChecked(checked)
            if checked:
                self.main_window.pause_btn.setText("▶️ 恢复所有提醒")
            else:
                self.main_window.pause_btn.setText("⏸️ 暂停所有提醒")
        self._update_menu_states()

    def _toggle_floating(self, checked):
        if checked:
            if self.floating_window is None:
                self.floating_window = FloatingWindow(self.engine)
            screen = QApplication.primaryScreen().geometry()
            self.floating_window.move(screen.width() - 180, 100)
            self.floating_window.show()
        else:
            if self.floating_window:
                self.floating_window.close()
                self.floating_window = None
        self._update_menu_states()

    def _show_history(self):
        self._show_main_window()
        if hasattr(self.main_window, 'tabs'):
            self.main_window.tabs.setCurrentIndex(3)

    def _show_settings(self):
        self._show_main_window()
        if hasattr(self.main_window, '_show_settings'):
            self.main_window._show_settings()

    def _quit(self):
        self.tray.hide()
        if self.floating_window:
            self.floating_window.close()
        QApplication.quit()

    def show_notification(self, title, message):
        self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 5000)
