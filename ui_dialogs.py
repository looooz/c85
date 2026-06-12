import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QDateTimeEdit, QTimeEdit, QCheckBox, QPushButton,
    QFileDialog, QGroupBox, QSlider, QDialogButtonBox,
    QWidget, QStackedWidget, QMessageBox,
)
from PyQt6.QtCore import Qt, QDateTime, QTime

import database
from theme import get_theme_manager


class AddReminderDialog(QDialog):
    def __init__(self, reminder_data=None, parent=None):
        super().__init__(parent)
        self.reminder_data = reminder_data
        self._editing = reminder_data is not None
        self.setWindowTitle("编辑提醒" if self._editing else "添加提醒")
        self.setMinimumWidth(450)
        self._init_ui()
        if self._editing:
            self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._form_layout = form

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("提醒标题")
        form.addRow("标题：", self.title_edit)

        self.content_edit = QTextEdit()
        self.content_edit.setMaximumHeight(80)
        self.content_edit.setPlaceholderText("提醒内容（可选）")
        form.addRow("内容：", self.content_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["单次", "每天", "每周", "每月", "每年"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("类型：", self.type_combo)

        self.datetime_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        form.addRow("时间：", self.datetime_edit)

        self.week_combo = QComboBox()
        self.week_combo.addItems(["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
        form.addRow("星期：", self.week_combo)
        self._week_row = form.rowCount() - 1

        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 31)
        form.addRow("日期：", self.month_spin)
        self._month_row = form.rowCount() - 1

        self.advance_combo = QComboBox()
        self.advance_combo.addItems(["不提前", "提前5分钟", "提前10分钟", "提前30分钟"])
        form.addRow("提前提醒：", self.advance_combo)

        self.enabled_check = QCheckBox("启用")
        self.enabled_check.setChecked(True)
        form.addRow("", self.enabled_check)

        layout.addLayout(form)

        sound_group = QGroupBox("提醒音效")
        sound_layout = QFormLayout()
        self.sound_combo = QComboBox()
        self.sound_combo.addItems(["默认", "铛声", "叮声", "警报", "柔和"])
        sound_layout.addRow("音效：", self.sound_combo)

        self.custom_sound_btn = QPushButton("选择自定义音效")
        self.custom_sound_btn.setCheckable(True)
        self.custom_sound_btn.toggled.connect(self._on_custom_sound_toggle)
        self.custom_sound_path = ""
        sound_layout.addRow("自定义：", self.custom_sound_btn)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_label = QLabel("80%")
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v}%")
        )
        vol_layout = QHBoxLayout()
        vol_layout.addWidget(self.volume_slider)
        vol_layout.addWidget(self.volume_label)
        sound_layout.addRow("音量：", vol_layout)

        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)

        buttons = QDialogButtonBox()
        ok_btn = buttons.addButton("确定", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        ok_btn.setObjectName("okButton")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._on_type_changed(0)

    def _on_type_changed(self, index):
        form = self._form_layout
        week_visible = (index == 2)
        month_visible = (index == 3)

        week_label_item = form.itemAt(self._week_row, QFormLayout.ItemRole.LabelRole)
        week_field_item = form.itemAt(self._week_row, QFormLayout.ItemRole.FieldRole)
        if week_label_item and week_label_item.widget():
            week_label_item.widget().setVisible(week_visible)
        if week_field_item and week_field_item.widget():
            week_field_item.widget().setVisible(week_visible)

        month_label_item = form.itemAt(self._month_row, QFormLayout.ItemRole.LabelRole)
        month_field_item = form.itemAt(self._month_row, QFormLayout.ItemRole.FieldRole)
        if month_label_item and month_label_item.widget():
            month_label_item.widget().setVisible(month_visible)
        if month_field_item and month_field_item.widget():
            month_field_item.widget().setVisible(month_visible)

        if index == 0:
            self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        elif index in (1, 2, 3, 4):
            self.datetime_edit.setDisplayFormat("HH:mm")

    def _on_custom_sound_toggle(self, checked):
        if checked:
            path, _ = QFileDialog.getOpenFileName(
                self, "选择音效文件", "", "音频文件 (*.wav *.mp3 *.ogg)"
            )
            if path:
                self.custom_sound_path = path
                self.custom_sound_btn.setText(os.path.basename(path))
            else:
                self.custom_sound_btn.setChecked(False)
                self.custom_sound_path = ""
        else:
            self.custom_sound_btn.setText("选择自定义音效")
            self.custom_sound_path = ""

    def _load_data(self):
        d = self.reminder_data
        self.title_edit.setText(d.get("title", ""))
        self.content_edit.setPlainText(d.get("content", ""))
        type_map = {"single": 0, "daily": 1, "weekly": 2, "monthly": 3, "yearly": 4}
        self.type_combo.setCurrentIndex(type_map.get(d.get("reminder_type", "single"), 0))
        try:
            dt = QDateTime.fromString(d.get("trigger_time", ""), "yyyy-MM-ddTHH:mm:ss")
            if not dt.isValid():
                dt = QDateTime.fromString(d.get("trigger_time", ""), "yyyy-MM-dd HH:mm:ss")
            self.datetime_edit.setDateTime(dt)
        except Exception:
            pass
        week_day = d.get("week_day")
        if week_day is not None:
            self.week_combo.setCurrentIndex(week_day)
        month_day = d.get("month_day")
        if month_day is not None:
            self.month_spin.setValue(month_day)
        advance_map = {0: 0, 5: 1, 10: 2, 30: 3}
        self.advance_combo.setCurrentIndex(advance_map.get(d.get("advance_minutes", 0), 0))
        self.enabled_check.setChecked(d.get("enabled", 1) == 1)
        sound_map = {"default": 0, "chime": 1, "ding": 2, "alert": 3, "gentle": 4}
        self.sound_combo.setCurrentIndex(sound_map.get(d.get("sound_type", "default"), 0))
        self.volume_slider.setValue(d.get("volume", 80))
        if d.get("sound_file"):
            self.custom_sound_path = d["sound_file"]
            self.custom_sound_btn.setChecked(True)
            self.custom_sound_btn.setText(os.path.basename(d["sound_file"]))

    def get_data(self):
        type_names = ["single", "daily", "weekly", "monthly", "yearly"]
        rtype = type_names[self.type_combo.currentIndex()]
        advance_values = [0, 5, 10, 30]
        advance = advance_values[self.advance_combo.currentIndex()]
        sound_names = ["default", "chime", "ding", "alert", "gentle"]
        sound_type = sound_names[self.sound_combo.currentIndex()]
        dt = self.datetime_edit.dateTime()
        trigger_time = dt.toString("yyyy-MM-ddTHH:mm:ss")
        data = {
            "title": self.title_edit.text().strip(),
            "content": self.content_edit.toPlainText().strip(),
            "reminder_type": rtype,
            "trigger_time": trigger_time,
            "advance_minutes": advance,
            "enabled": self.enabled_check.isChecked(),
            "sound_type": sound_type,
            "sound_file": self.custom_sound_path if self.custom_sound_path else None,
            "volume": self.volume_slider.value(),
        }
        if rtype == "weekly":
            data["week_day"] = self.week_combo.currentIndex()
        if rtype == "monthly":
            data["month_day"] = self.month_spin.value()
        return data


import os


class AddCountdownDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加倒计时")
        self.setMinimumWidth(350)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("倒计时标题")
        form.addRow("标题：", self.title_edit)

        time_layout = QHBoxLayout()
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 99)
        self.hours_spin.setValue(0)
        time_layout.addWidget(QLabel("时"))
        time_layout.addWidget(self.hours_spin)

        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setValue(25)
        time_layout.addWidget(QLabel("分"))
        time_layout.addWidget(self.minutes_spin)

        self.seconds_spin = QSpinBox()
        self.seconds_spin.setRange(0, 59)
        self.seconds_spin.setValue(0)
        time_layout.addWidget(QLabel("秒"))
        time_layout.addWidget(self.seconds_spin)

        form.addRow("时长：", time_layout)

        layout.addLayout(form)

        buttons = QDialogButtonBox()
        ok_btn = buttons.addButton("确定", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        ok_btn.setObjectName("okButton")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        total = (
            self.hours_spin.value() * 3600
            + self.minutes_spin.value() * 60
            + self.seconds_spin.value()
        )
        return {
            "title": self.title_edit.text().strip() or "倒计时",
            "duration_seconds": total,
        }


class AddIntervalDialog(QDialog):
    def __init__(self, interval_data=None, parent=None):
        super().__init__(parent)
        self.interval_data = interval_data
        self._editing = interval_data is not None
        self.setWindowTitle("编辑间隔提醒" if self._editing else "添加间隔提醒")
        self.setMinimumWidth(400)
        self._init_ui()
        if self._editing:
            self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("如：喝水提醒")
        form.addRow("标题：", self.title_edit)

        self.content_edit = QTextEdit()
        self.content_edit.setMaximumHeight(60)
        self.content_edit.setPlaceholderText("提醒内容（可选）")
        form.addRow("内容：", self.content_edit)

        interval_layout = QHBoxLayout()
        self.interval_value = QSpinBox()
        self.interval_value.setRange(1, 999)
        self.interval_value.setValue(30)
        self.interval_unit = QComboBox()
        self.interval_unit.addItems(["分钟", "小时"])
        interval_layout.addWidget(self.interval_value)
        interval_layout.addWidget(self.interval_unit)
        form.addRow("间隔：", interval_layout)

        time_range_layout = QHBoxLayout()
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        self.start_time.setTime(QTime(9, 0))
        self.start_time.setSpecialValueText("不限制")
        time_range_layout.addWidget(QLabel("从"))
        time_range_layout.addWidget(self.start_time)

        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        self.end_time.setTime(QTime(18, 0))
        self.end_time.setSpecialValueText("不限制")
        time_range_layout.addWidget(QLabel("到"))
        time_range_layout.addWidget(self.end_time)
        form.addRow("活跃时段：", time_range_layout)

        self.enabled_check = QCheckBox("启用")
        self.enabled_check.setChecked(True)
        form.addRow("", self.enabled_check)

        sound_layout = QHBoxLayout()
        self.sound_combo = QComboBox()
        self.sound_combo.addItems(["默认", "铛声", "叮声", "警报", "柔和"])
        sound_layout.addWidget(self.sound_combo)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_label = QLabel("80%")
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v}%")
        )
        sound_layout.addWidget(self.volume_slider)
        sound_layout.addWidget(self.volume_label)
        form.addRow("音效/音量：", sound_layout)

        layout.addLayout(form)

        buttons = QDialogButtonBox()
        ok_btn = buttons.addButton("确定", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        ok_btn.setObjectName("okButton")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_data(self):
        d = self.interval_data
        self.title_edit.setText(d.get("title", ""))
        self.content_edit.setPlainText(d.get("content", ""))
        iv_minutes = d.get("interval_minutes", 30)
        if iv_minutes >= 60 and iv_minutes % 60 == 0:
            self.interval_value.setValue(iv_minutes // 60)
            self.interval_unit.setCurrentIndex(1)
        else:
            self.interval_value.setValue(iv_minutes)
            self.interval_unit.setCurrentIndex(0)
        if d.get("start_time"):
            parts = d["start_time"].split(":")
            self.start_time.setTime(QTime(int(parts[0]), int(parts[1])))
        if d.get("end_time"):
            parts = d["end_time"].split(":")
            self.end_time.setTime(QTime(int(parts[0]), int(parts[1])))
        self.enabled_check.setChecked(d.get("enabled", 1) == 1)
        sound_map = {"default": 0, "chime": 1, "ding": 2, "alert": 3, "gentle": 4}
        self.sound_combo.setCurrentIndex(sound_map.get(d.get("sound_type", "default"), 0))
        self.volume_slider.setValue(d.get("volume", 80))

    def get_data(self):
        val = self.interval_value.value()
        if self.interval_unit.currentIndex() == 1:
            val *= 60
        sound_names = ["default", "chime", "ding", "alert", "gentle"]
        return {
            "title": self.title_edit.text().strip() or "间隔提醒",
            "content": self.content_edit.toPlainText().strip(),
            "interval_minutes": val,
            "start_time": self.start_time.time().toString("HH:mm"),
            "end_time": self.end_time.time().toString("HH:mm"),
            "enabled": self.enabled_check.isChecked(),
            "sound_type": sound_names[self.sound_combo.currentIndex()],
            "volume": self.volume_slider.value(),
        }


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(450)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        chime_group = QGroupBox("整点报时")
        chime_layout = QFormLayout()

        self.chime_enabled = QCheckBox("启用整点报时")
        chime_layout.addRow(self.chime_enabled)

        chime_time_layout = QHBoxLayout()
        self.chime_start = QSpinBox()
        self.chime_start.setRange(0, 23)
        chime_time_layout.addWidget(QLabel("从"))
        chime_time_layout.addWidget(self.chime_start)
        chime_time_layout.addWidget(QLabel("点到"))
        self.chime_end = QSpinBox()
        self.chime_end.setRange(0, 23)
        chime_time_layout.addWidget(self.chime_end)
        chime_time_layout.addWidget(QLabel("点"))
        chime_layout.addRow("报时时段：", chime_time_layout)

        self.chime_sound = QComboBox()
        self.chime_sound.addItems(["铛铛声", "叮声", "警报", "柔和"])
        chime_layout.addRow("报时音效：", self.chime_sound)

        self.tts_enabled = QCheckBox("语音播报时间")
        chime_layout.addRow(self.tts_enabled)

        chime_group.setLayout(chime_layout)
        layout.addWidget(chime_group)

        focus_group = QGroupBox("专注模式（白名单）")
        focus_layout = QFormLayout()

        self.focus_enabled = QCheckBox("启用专注模式")
        focus_layout.addRow(self.focus_enabled)

        focus_time_layout = QHBoxLayout()
        self.focus_start = QTimeEdit()
        self.focus_start.setDisplayFormat("HH:mm")
        focus_time_layout.addWidget(QLabel("从"))
        focus_time_layout.addWidget(self.focus_start)
        self.focus_end = QTimeEdit()
        self.focus_end.setDisplayFormat("HH:mm")
        focus_time_layout.addWidget(QLabel("到"))
        focus_time_layout.addWidget(self.focus_end)
        focus_layout.addRow("专注时段：", focus_time_layout)

        self.fullscreen_whitelist = QCheckBox("全屏时自动屏蔽提醒")
        focus_layout.addRow(self.fullscreen_whitelist)

        focus_group.setLayout(focus_layout)
        layout.addWidget(focus_group)

        default_group = QGroupBox("默认设置")
        default_layout = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_manager = get_theme_manager()
        for key, name in self.theme_manager.get_all_themes():
            self.theme_combo.addItem(name, key)
        default_layout.addRow("界面主题：", self.theme_combo)

        self.default_volume = QSlider(Qt.Orientation.Horizontal)
        self.default_volume.setRange(0, 100)
        self.default_volume_label = QLabel("80%")
        self.default_volume.valueChanged.connect(
            lambda v: self.default_volume_label.setText(f"{v}%")
        )
        vol_layout = QHBoxLayout()
        vol_layout.addWidget(self.default_volume)
        vol_layout.addWidget(self.default_volume_label)
        default_layout.addRow("默认音量：", vol_layout)
        default_group.setLayout(default_layout)
        layout.addWidget(default_group)

        buttons = QDialogButtonBox()
        ok_btn = buttons.addButton("确定", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        ok_btn.setObjectName("okButton")
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_settings(self):
        self.chime_enabled.setChecked(database.get_setting("hourly_chime_enabled", "0") == "1")
        self.chime_start.setValue(int(database.get_setting("hourly_chime_start", "9")))
        self.chime_end.setValue(int(database.get_setting("hourly_chime_end", "21")))
        sound_map = {"chime": 0, "ding": 1, "alert": 2, "gentle": 3}
        self.chime_sound.setCurrentIndex(sound_map.get(database.get_setting("hourly_chime_sound", "chime"), 0))
        self.tts_enabled.setChecked(database.get_setting("tts_enabled", "0") == "1")
        self.focus_enabled.setChecked(database.get_setting("focus_mode_enabled", "0") == "1")
        focus_start = database.get_setting("focus_mode_start", "")
        focus_end = database.get_setting("focus_mode_end", "")
        if focus_start:
            parts = focus_start.split(":")
            self.focus_start.setTime(QTime(int(parts[0]), int(parts[1])))
        if focus_end:
            parts = focus_end.split(":")
            self.focus_end.setTime(QTime(int(parts[0]), int(parts[1])))
        self.fullscreen_whitelist.setChecked(database.get_setting("whitelist_fullscreen", "1") == "1")
        self.default_volume.setValue(int(database.get_setting("default_volume", "80")))
        theme = database.get_setting("theme", "dark")
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

    def _save_and_accept(self):
        database.set_setting("hourly_chime_enabled", "1" if self.chime_enabled.isChecked() else "0")
        database.set_setting("hourly_chime_start", str(self.chime_start.value()))
        database.set_setting("hourly_chime_end", str(self.chime_end.value()))
        sound_names = ["chime", "ding", "alert", "gentle"]
        database.set_setting("hourly_chime_sound", sound_names[self.chime_sound.currentIndex()])
        database.set_setting("tts_enabled", "1" if self.tts_enabled.isChecked() else "0")
        database.set_setting("focus_mode_enabled", "1" if self.focus_enabled.isChecked() else "0")
        database.set_setting("focus_mode_start", self.focus_start.time().toString("HH:mm"))
        database.set_setting("focus_mode_end", self.focus_end.time().toString("HH:mm"))
        database.set_setting("whitelist_fullscreen", "1" if self.fullscreen_whitelist.isChecked() else "0")
        database.set_setting("default_volume", str(self.default_volume.value()))
        database.set_setting("theme", self.theme_combo.currentData())
        self.accept()


class NotificationPopup(QWidget):
    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager(self)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._flash_count = 0
        self._init_ui(title, content)
        self._flash_timer = None

    def _init_ui(self, title, content):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        inner = QWidget(self)
        inner.setObjectName("notificationInner")
        self._inner_widget = inner
        inner_layout = QVBoxLayout(inner)

        self.title_label = QLabel(f"🔔 {title}")
        self.title_label.setObjectName("notificationTitle")
        inner_layout.addWidget(self.title_label)

        self.content_label = None
        if content:
            self.content_label = QLabel(content)
            self.content_label.setObjectName("notificationContent")
            self.content_label.setWordWrap(True)
            inner_layout.addWidget(self.content_label)

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("notificationCloseBtn")
        close_btn.clicked.connect(self.close)
        inner_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addWidget(inner)
        self.setFixedSize(320, 160)
        self._apply_theme()

    def _apply_theme(self):
        theme = self.theme_manager.get_theme()
        self._inner_widget.setStyleSheet(f"""
            #notificationInner {{
                background: {theme['notification_bg']};
                border-radius: 12px;
                border: 2px solid {theme['notification_border']};
            }}
        """)
        self.title_label.setStyleSheet(f"""
            color: {theme['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        if self.content_label:
            self.content_label.setStyleSheet(f"""
                color: {theme['text_secondary']};
                font-size: 13px;
            """)

    def show_at_bottom_right(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 80
        self.move(x, y)
        self.show()
        self._start_flash()

    def _start_flash(self):
        from PyQt6.QtCore import QTimer
        self._flash_timer = QTimer(self)
        self._flash_count = 0
        self._flash_timer.timeout.connect(self._do_flash)
        self._flash_timer.start(500)

    def _do_flash(self):
        self._flash_count += 1
        if self._flash_count > 6:
            self._flash_timer.stop()
            return
        if self._flash_count % 2 == 1:
            self.setWindowOpacity(0.3)
        else:
            self.setWindowOpacity(1.0)
