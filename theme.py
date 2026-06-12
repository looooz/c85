from PyQt6.QtCore import QObject, pyqtSignal

import database


DARK_THEME = {
    "name": "dark",
    "display_name": "深色主题",
    "bg_main": "#1a1a2e",
    "bg_secondary": "#16213e",
    "bg_card": "#16213e",
    "bg_tertiary": "#0f3460",
    "accent": "#e94560",
    "accent_hover": "#ff6b81",
    "accent_active": "#c0392b",
    "text_primary": "#e0e0e0",
    "text_secondary": "#a0a0b0",
    "text_accent": "#e94560",
    "text_success": "#27ae60",
    "text_error": "#e74c3c",
    "text_warning": "#f39c12",
    "border": "#1a1a2e",
    "border_accent": "#0f3460",
    "grid_line": "#1a1a2e",
    "selection_bg": "#0f3460",
    "selection_text": "#ffffff",
    "alternate_row": "#1a1a2e",
    "notification_bg": "#2c3e50",
    "notification_border": "#3498db",
    "tray_icon_bg": "#e94560",
    "tray_icon_text": "#ffffff",
    "button_bg": "#0f3460",
    "button_text": "#e0e0e0",
    "button_hover_bg": "#e94560",
    "button_hover_text": "#ffffff",
    "button_pressed_bg": "#c0392b",
    "progress_bg": "#16213e",
    "progress_bar": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e94560, stop:1 #ff6b81)",
}

LIGHT_THEME = {
    "name": "light",
    "display_name": "浅色主题",
    "bg_main": "#f5f7fa",
    "bg_secondary": "#ffffff",
    "bg_card": "#ffffff",
    "bg_tertiary": "#e8ecf1",
    "accent": "#e94560",
    "accent_hover": "#ff6b81",
    "accent_active": "#c0392b",
    "text_primary": "#2c3e50",
    "text_secondary": "#7f8c8d",
    "text_accent": "#e94560",
    "text_success": "#27ae60",
    "text_error": "#e74c3c",
    "text_warning": "#f39c12",
    "border": "#dcdfe6",
    "border_accent": "#e94560",
    "grid_line": "#ebeef5",
    "selection_bg": "#e94560",
    "selection_text": "#ffffff",
    "alternate_row": "#f5f7fa",
    "notification_bg": "#ffffff",
    "notification_border": "#e94560",
    "tray_icon_bg": "#e94560",
    "tray_icon_text": "#ffffff",
    "button_bg": "#e94560",
    "button_text": "#ffffff",
    "button_hover_bg": "#ff6b81",
    "button_hover_text": "#ffffff",
    "button_pressed_bg": "#c0392b",
    "progress_bg": "#e8ecf1",
    "progress_bar": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e94560, stop:1 #ff6b81)",
}


THEMES = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}


class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_theme = "dark"
        self._load_theme()

    def _load_theme(self):
        saved = database.get_setting("theme", "dark")
        if saved in THEMES:
            self._current_theme = saved
        else:
            self._current_theme = "dark"

    def get_current_theme(self):
        return self._current_theme

    def get_theme(self):
        return THEMES.get(self._current_theme, DARK_THEME)

    def set_theme(self, theme_name):
        if theme_name in THEMES and theme_name != self._current_theme:
            self._current_theme = theme_name
            database.set_setting("theme", theme_name)
            self.theme_changed.emit(theme_name)

    def get_all_themes(self):
        return [(k, v["display_name"]) for k, v in THEMES.items()]

    def get_color(self, color_name):
        theme = self.get_theme()
        return theme.get(color_name, "#000000")

    def get_stylesheet(self):
        t = self.get_theme()
        name = t["name"]

        if name == "dark":
            return self._get_dark_stylesheet(t)
        else:
            return self._get_light_stylesheet(t)

    def _get_dark_stylesheet(self, t):
        return f"""
        QMainWindow {{
            background: {t['bg_main']};
        }}
        QWidget {{
            color: {t['text_primary']};
            font-size: 13px;
        }}
        QTabWidget::pane {{
            border: 1px solid {t['bg_tertiary']};
            background: {t['bg_main']};
            border-radius: 4px;
        }}
        QTabBar::tab {{
            background: {t['bg_secondary']};
            color: {t['text_secondary']};
            padding: 8px 20px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 2px;
            font-size: 13px;
        }}
        QTabBar::tab:selected {{
            background: {t['bg_tertiary']};
            color: {t['accent']};
            font-weight: bold;
        }}
        QTabBar::tab:hover {{
            background: {t['bg_tertiary']};
        }}
        QTableWidget {{
            background: {t['bg_secondary']};
            color: {t['text_primary']};
            gridline-color: {t['grid_line']};
            border: none;
            selection-background-color: {t['selection_bg']};
            selection-color: {t['selection_text']};
            font-size: 13px;
            border-radius: 6px;
        }}
        QTableWidget::item {{
            padding: 6px;
        }}
        QHeaderView::section {{
            background: {t['bg_tertiary']};
            color: {t['accent']};
            padding: 6px;
            border: none;
            font-weight: bold;
            font-size: 12px;
        }}
        QPushButton {{
            background: {t['bg_tertiary']};
            color: {t['text_primary']};
            border: 1px solid {t['border']};
            border-radius: 6px;
            padding: 7px 16px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background: {t['accent']};
            color: #ffffff;
            border-color: {t['accent']};
        }}
        QPushButton:pressed {{
            background: {t['accent_active']};
        }}
        QPushButton:checked {{
            background: {t['accent']};
            color: #ffffff;
        }}
        QPushButton#addBtn {{
            background: {t['accent']};
            color: white;
            font-weight: bold;
            border-radius: 8px;
            padding: 10px 24px;
            font-size: 14px;
        }}
        QPushButton#addBtn:hover {{
            background: {t['accent_hover']};
        }}
        QPushButton#pauseBtn {{
            background: {t['text_warning']};
            color: white;
        }}
        QPushButton#pauseBtn:hover {{
            background: #e67e22;
        }}
        QPushButton#focusBtn {{
            background: {t['text_success']};
            color: white;
        }}
        QPushButton#focusBtn:hover {{
            background: #2ecc71;
        }}
        QPushButton#focusBtn:checked {{
            background: {t['accent']};
        }}
        QGroupBox {{
            color: {t['accent']};
            border: 1px solid {t['bg_tertiary']};
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 16px;
            font-weight: bold;
            font-size: 13px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }}
        QLabel {{
            color: {t['text_primary']};
            font-size: 13px;
        }}
        QLabel#countdownLabel {{
            color: {t['accent']};
            font-size: 22px;
            font-weight: bold;
        }}
        QLabel#intervalStatusLabel {{
            color: {t['text_warning']};
            font-size: 13px;
        }}
        QProgressBar {{
            background: {t['bg_secondary']};
            border: 1px solid {t['bg_tertiary']};
            border-radius: 6px;
            text-align: center;
            color: white;
            font-size: 12px;
            height: 20px;
        }}
        QProgressBar::chunk {{
            background: {t['progress_bar']};
            border-radius: 5px;
        }}
        QCheckBox {{
            color: {t['text_primary']};
            font-size: 13px;
        }}
        QDateEdit, QTimeEdit, QDateTimeEdit, QSpinBox, QComboBox, QLineEdit, QTextEdit {{
            background: {t['bg_secondary']};
            color: {t['text_primary']};
            border: 1px solid {t['bg_tertiary']};
            border-radius: 4px;
            padding: 4px 8px;
            selection-background-color: {t['selection_bg']};
            selection-color: {t['selection_text']};
        }}
        QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus, QSpinBox:focus, QComboBox:focus, QLineEdit:focus, QTextEdit:focus {{
            border: 1px solid {t['accent']};
        }}
        QComboBox QAbstractItemView {{
            background: {t['bg_secondary']};
            color: {t['text_primary']};
            selection-background-color: {t['selection_bg']};
            selection-color: {t['selection_text']};
            border: 1px solid {t['bg_tertiary']};
        }}
        QStatusBar {{
            background: {t['bg_secondary']};
            color: {t['text_secondary']};
            font-size: 12px;
        }}
        QToolBar {{
            background: {t['bg_secondary']};
            border: none;
            spacing: 8px;
            padding: 4px;
        }}
        QSplitter::handle {{
            background: {t['bg_tertiary']};
        }}
        QFrame#cardFrame {{
            background: {t['bg_card']};
            border-radius: 8px;
            border: 1px solid {t['bg_tertiary']};
        }}
        QScrollBar:vertical {{
            background: {t['bg_main']};
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {t['bg_tertiary']};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {t['accent']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QMenu {{
            background: {t['bg_secondary']};
            color: {t['text_primary']};
            border: 1px solid {t['bg_tertiary']};
            border-radius: 6px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 8px 20px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background: {t['accent']};
            color: white;
        }}
        QMenu::separator {{
            height: 1px;
            background: {t['bg_tertiary']};
            margin: 4px 8px;
        }}
        QDialog {{
            background: {t['bg_main']};
        }}
        QDialogButtonBox QPushButton {{
            min-width: 80px;
        }}
        """

    def _get_light_stylesheet(self, t):
        return f"""
        QMainWindow {{
            background: {t['bg_main']};
        }}
        QWidget {{
            color: {t['text_primary']};
            font-size: 13px;
        }}
        QTabWidget::pane {{
            border: 1px solid {t['border']};
            background: {t['bg_secondary']};
            border-radius: 4px;
        }}
        QTabBar::tab {{
            background: {t['bg_tertiary']};
            color: {t['text_secondary']};
            padding: 8px 20px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 2px;
            font-size: 13px;
        }}
        QTabBar::tab:selected {{
            background: {t['bg_secondary']};
            color: {t['accent']};
            font-weight: bold;
        }}
        QTabBar::tab:hover {{
            background: {t['bg_secondary']};
        }}
        QTableWidget {{
            background: {t['bg_secondary']};
            color: {t['text_primary']};
            gridline-color: {t['grid_line']};
            border: 1px solid {t['border']};
            selection-background-color: {t['selection_bg']};
            selection-color: {t['selection_text']};
            font-size: 13px;
            border-radius: 6px;
        }}
        QTableWidget::item {{
            padding: 6px;
        }}
        QHeaderView::section {{
            background: {t['bg_tertiary']};
            color: {t['accent']};
            padding: 6px;
            border: none;
            border-bottom: 2px solid {t['accent']};
            font-weight: bold;
            font-size: 12px;
        }}
        QPushButton {{
            background: {t['bg_secondary']};
            color: {t['text_primary']};
            border: 1px solid {t['border']};
            border-radius: 6px;
            padding: 7px 16px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background: {t['accent']};
            color: #ffffff;
            border-color: {t['accent']};
        }}
        QPushButton:pressed {{
            background: {t['accent_active']};
        }}
        QPushButton:checked {{
            background: {t['accent']};
            color: #ffffff;
        }}
        QPushButton#addBtn {{
            background: {t['accent']};
            color: white;
            font-weight: bold;
            border-radius: 8px;
            padding: 10px 24px;
            font-size: 14px;
        }}
        QPushButton#addBtn:hover {{
            background: {t['accent_hover']};
        }}
        QPushButton#pauseBtn {{
            background: {t['text_warning']};
            color: white;
            border-color: {t['text_warning']};
        }}
        QPushButton#pauseBtn:hover {{
            background: #e67e22;
            border-color: #e67e22;
        }}
        QPushButton#focusBtn {{
            background: {t['text_success']};
            color: white;
            border-color: {t['text_success']};
        }}
        QPushButton#focusBtn:hover {{
            background: #2ecc71;
            border-color: #2ecc71;
        }}
        QPushButton#focusBtn:checked {{
            background: {t['accent']};
            border-color: {t['accent']};
        }}
        QGroupBox {{
            color: {t['accent']};
            border: 1px solid {t['border']};
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 16px;
            font-weight: bold;
            font-size: 13px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            background: {t['bg_main']};
        }}
        QLabel {{
            color: {t['text_primary']};
            font-size: 13px;
        }}
        QLabel#countdownLabel {{
            color: {t['accent']};
            font-size: 22px;
            font-weight: bold;
        }}
        QLabel#intervalStatusLabel {{
            color: {t['text_warning']};
            font-size: 13px;
        }}
        QProgressBar {{
            background: {t['progress_bg']};
            border: 1px solid {t['border']};
            border-radius: 6px;
            text-align: center;
            color: {t['text_primary']};
            font-size: 12px;
            height: 20px;
        }}
        QProgressBar::chunk {{
            background: {t['progress_bar']};
            border-radius: 5px;
        }}
        QCheckBox {{
            color: {t['text_primary']};
            font-size: 13px;
        }}
        QDateEdit, QTimeEdit, QDateTimeEdit, QSpinBox, QComboBox, QLineEdit, QTextEdit {{
            background: {t['bg_secondary']};
            color: {t['text_primary']};
            border: 1px solid {t['border']};
            border-radius: 4px;
            padding: 4px 8px;
            selection-background-color: {t['selection_bg']};
            selection-color: {t['selection_text']};
        }}
        QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus, QSpinBox:focus, QComboBox:focus, QLineEdit:focus, QTextEdit:focus {{
            border: 1px solid {t['accent']};
        }}
        QComboBox QAbstractItemView {{
            background: {t['bg_secondary']};
            color: {t['text_primary']};
            selection-background-color: {t['selection_bg']};
            selection-color: {t['selection_text']};
            border: 1px solid {t['border']};
        }}
        QStatusBar {{
            background: {t['bg_secondary']};
            color: {t['text_secondary']};
            font-size: 12px;
            border-top: 1px solid {t['border']};
        }}
        QToolBar {{
            background: {t['bg_secondary']};
            border: none;
            spacing: 8px;
            padding: 4px;
            border-bottom: 1px solid {t['border']};
        }}
        QSplitter::handle {{
            background: {t['border']};
        }}
        QFrame#cardFrame {{
            background: {t['bg_card']};
            border-radius: 8px;
            border: 1px solid {t['border']};
        }}
        QScrollBar:vertical {{
            background: {t['bg_main']};
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {t['border']};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {t['accent']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QMenu {{
            background: {t['bg_secondary']};
            color: {t['text_primary']};
            border: 1px solid {t['border']};
            border-radius: 6px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 8px 20px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background: {t['accent']};
            color: white;
        }}
        QMenu::separator {{
            height: 1px;
            background: {t['border']};
            margin: 4px 8px;
        }}
        QDialog {{
            background: {t['bg_main']};
        }}
        QDialogButtonBox QPushButton {{
            min-width: 80px;
        }}
        """


_theme_instance = None


def get_theme_manager(parent=None):
    global _theme_instance
    if _theme_instance is None:
        _theme_instance = ThemeManager(parent)
    return _theme_instance
