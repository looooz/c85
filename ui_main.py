from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QLabel, QProgressBar, QGroupBox, QSplitter, QFrame,
    QAbstractItemView, QMessageBox, QDateEdit, QCheckBox,
    QToolBar, QStatusBar, QApplication, QStyle, QDialog,
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QFont, QColor

import database
from core import ReminderEngine, AudioManager, FocusModeManager
from ui_dialogs import (
    AddReminderDialog, AddCountdownDialog, AddIntervalDialog,
    SettingsDialog, NotificationPopup,
)


STYLESHEET = """
QMainWindow {
    background: #1a1a2e;
}
QTabWidget::pane {
    border: 1px solid #16213e;
    background: #1a1a2e;
    border-radius: 4px;
}
QTabBar::tab {
    background: #16213e;
    color: #a0a0b0;
    padding: 8px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-size: 13px;
}
QTabBar::tab:selected {
    background: #0f3460;
    color: #e94560;
    font-weight: bold;
}
QTabBar::tab:hover {
    background: #0f3460;
}
QTableWidget {
    background: #16213e;
    color: #e0e0e0;
    gridline-color: #1a1a2e;
    border: none;
    selection-background-color: #0f3460;
    selection-color: #ffffff;
    font-size: 13px;
}
QTableWidget::item {
    padding: 6px;
}
QHeaderView::section {
    background: #0f3460;
    color: #e94560;
    padding: 6px;
    border: none;
    font-weight: bold;
    font-size: 12px;
}
QPushButton {
    background: #0f3460;
    color: #e0e0e0;
    border: 1px solid #1a1a2e;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
}
QPushButton:hover {
    background: #e94560;
    color: #ffffff;
}
QPushButton:pressed {
    background: #c0392b;
}
QPushButton#addBtn {
    background: #e94560;
    color: white;
    font-weight: bold;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
}
QPushButton#addBtn:hover {
    background: #ff6b81;
}
QPushButton#pauseBtn {
    background: #f39c12;
    color: white;
}
QPushButton#pauseBtn:hover {
    background: #e67e22;
}
QPushButton#focusBtn {
    background: #27ae60;
    color: white;
}
QPushButton#focusBtn:hover {
    background: #2ecc71;
}
QPushButton#focusBtn:checked {
    background: #e94560;
}
QGroupBox {
    color: #e94560;
    border: 1px solid #0f3460;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 16px;
    font-weight: bold;
    font-size: 13px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QLabel {
    color: #e0e0e0;
    font-size: 13px;
}
QLabel#countdownLabel {
    color: #e94560;
    font-size: 22px;
    font-weight: bold;
}
QLabel#intervalStatusLabel {
    color: #f39c12;
    font-size: 13px;
}
QProgressBar {
    background: #16213e;
    border: 1px solid #0f3460;
    border-radius: 6px;
    text-align: center;
    color: white;
    font-size: 12px;
    height: 20px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #e94560, stop:1 #ff6b81);
    border-radius: 5px;
}
QCheckBox {
    color: #e0e0e0;
    font-size: 13px;
}
QDateEdit {
    background: #16213e;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    border-radius: 4px;
    padding: 4px;
}
QStatusBar {
    background: #16213e;
    color: #a0a0b0;
    font-size: 12px;
}
QToolBar {
    background: #16213e;
    border: none;
    spacing: 8px;
    padding: 4px;
}
QSplitter::handle {
    background: #0f3460;
}
QFrame#cardFrame {
    background: #16213e;
    border-radius: 8px;
    border: 1px solid #0f3460;
}
"""


class ReminderListTab(QWidget):
    def __init__(self, engine: ReminderEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        toolbar = QHBoxLayout()
        add_btn = QPushButton("➕ 添加提醒")
        add_btn.setObjectName("addBtn")
        add_btn.clicked.connect(self._add_reminder)
        toolbar.addWidget(add_btn)

        edit_btn = QPushButton("✏️ 编辑")
        edit_btn.clicked.connect(self._edit_reminder)
        toolbar.addWidget(edit_btn)

        del_btn = QPushButton("🗑️ 删除")
        del_btn.clicked.connect(self._delete_reminder)
        toolbar.addWidget(del_btn)

        toggle_btn = QPushButton("🔄 切换启用")
        toggle_btn.clicked.connect(self._toggle_reminder)
        toolbar.addWidget(toggle_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "标题", "类型", "触发时间", "提前", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("alternate-background-color: #1a1a2e;")
        layout.addWidget(self.table)

    def _load_data(self):
        reminders = database.get_reminders()
        self.table.setRowCount(len(reminders))
        type_labels = {"single": "单次", "daily": "每天", "weekly": "每周", "monthly": "每月", "yearly": "每年"}
        for row, r in enumerate(reminders):
            self.table.setItem(row, 0, QTableWidgetItem(str(r["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(r["title"]))
            self.table.setItem(row, 2, QTableWidgetItem(type_labels.get(r["reminder_type"], r["reminder_type"])))
            try:
                dt = datetime.fromisoformat(r["trigger_time"])
                time_str = dt.strftime("%Y-%m-%d %H:%M") if r["reminder_type"] == "single" else dt.strftime("每天 %H:%M") if r["reminder_type"] == "daily" else dt.strftime("%H:%M")
                if r["reminder_type"] == "weekly":
                    days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                    time_str = f"{days[r.get('week_day', 0)]} {dt.strftime('%H:%M')}"
                elif r["reminder_type"] == "monthly":
                    time_str = f"每月{r.get('month_day', 1)}日 {dt.strftime('%H:%M')}"
                elif r["reminder_type"] == "yearly":
                    time_str = f"每年{dt.strftime('%m月%d日')} {dt.strftime('%H:%M')}"
            except (ValueError, TypeError):
                time_str = r["trigger_time"]
            self.table.setItem(row, 3, QTableWidgetItem(time_str))
            advance = r.get("advance_minutes", 0)
            self.table.setItem(row, 4, QTableWidgetItem(f"提前{advance}分" if advance > 0 else "无"))
            status = "✅ 启用" if r.get("enabled", 1) else "⏸️ 停用"
            item = QTableWidgetItem(status)
            item.setForeground(QColor("#27ae60") if r.get("enabled", 1) else QColor("#e74c3c"))
            self.table.setItem(row, 5, item)

    def _add_reminder(self):
        dlg = AddReminderDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["title"]:
                return
            database.add_reminder(data)
            self._load_data()

    def _edit_reminder(self):
        row = self.table.currentRow()
        if row < 0:
            return
        rid = int(self.table.item(row, 0).text())
        r = database.get_reminder_by_id(rid)
        if not r:
            return
        dlg = AddReminderDialog(reminder_data=r, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            database.update_reminder(rid, data)
            self._load_data()

    def _delete_reminder(self):
        row = self.table.currentRow()
        if row < 0:
            return
        rid = int(self.table.item(row, 0).text())
        name = self.table.item(row, 1).text()
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除提醒「{name}」吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.delete_reminder(rid)
            self._load_data()

    def _toggle_reminder(self):
        row = self.table.currentRow()
        if row < 0:
            return
        rid = int(self.table.item(row, 0).text())
        r = database.get_reminder_by_id(rid)
        if r:
            database.update_reminder(rid, {"enabled": not r.get("enabled", 1)})
            self._load_data()

    def refresh(self):
        self._load_data()


class CountdownTab(QWidget):
    def __init__(self, engine: ReminderEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._init_ui()
        self._load_data()
        engine.countdown_tick.connect(self._load_data)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        toolbar = QHBoxLayout()
        add_btn = QPushButton("➕ 添加倒计时")
        add_btn.setObjectName("addBtn")
        add_btn.clicked.connect(self._add_countdown)
        toolbar.addWidget(add_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.scroll_layout = QVBoxLayout()
        layout.addLayout(self.scroll_layout)
        layout.addStretch()

    def _load_data(self):
        for i in reversed(range(self.scroll_layout.count())):
            w = self.scroll_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        countdowns = database.get_countdowns(active_only=True)
        for cd in countdowns:
            card = self._create_countdown_card(cd)
            self.scroll_layout.addWidget(card)

        if not countdowns:
            label = QLabel("暂无进行中的倒计时")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #a0a0b0; font-size: 14px; padding: 40px;")
            self.scroll_layout.addWidget(label)

    def _create_countdown_card(self, cd):
        card = QFrame()
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)

        top = QHBoxLayout()
        title = QLabel(f"⏱ {cd['title']}")
        title.setStyleSheet("color: #e0e0e0; font-size: 15px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()

        remaining = self.engine.get_countdown_remaining(cd["id"])
        total = cd.get("duration_seconds", 1)
        progress = max(0, min(100, int((1 - remaining / max(total, 1)) * 100)))

        bar = QProgressBar()
        bar.setValue(progress)
        bar.setTextVisible(True)
        bar.setFormat(f"{progress}%")
        top.addWidget(bar)
        card_layout.addLayout(top)

        mins, secs = divmod(max(0, remaining), 60)
        hours, mins = divmod(mins, 60)
        time_label = QLabel(f"{hours:02d}:{mins:02d}:{secs:02d}")
        time_label.setObjectName("countdownLabel")
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(time_label)

        btn_layout = QHBoxLayout()
        if cd.get("is_running", 1):
            pause_btn = QPushButton("⏸ 暂停")
            pause_btn.clicked.connect(lambda checked, cid=cd["id"]: self._pause_countdown(cid))
            btn_layout.addWidget(pause_btn)
        else:
            resume_btn = QPushButton("▶ 继续")
            resume_btn.clicked.connect(lambda checked, cid=cd["id"]: self._resume_countdown(cid))
            btn_layout.addWidget(resume_btn)
        cancel_btn = QPushButton("✖ 取消")
        cancel_btn.clicked.connect(lambda checked, cid=cd["id"]: self._cancel_countdown(cid))
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        card_layout.addLayout(btn_layout)

        return card

    def _add_countdown(self):
        dlg = AddCountdownDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if data["duration_seconds"] <= 0:
                return
            cid = database.add_countdown(data)
            self.engine.start_countdown(cid, data["duration_seconds"])
            self._load_data()

    def _pause_countdown(self, cid):
        self.engine.pause_countdown(cid)
        self._load_data()

    def _resume_countdown(self, cid):
        self.engine.resume_countdown(cid)
        self._load_data()

    def _cancel_countdown(self, cid):
        self.engine.remove_countdown(cid)
        self._load_data()


class IntervalTab(QWidget):
    def __init__(self, engine: ReminderEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        toolbar = QHBoxLayout()
        add_btn = QPushButton("➕ 添加间隔提醒")
        add_btn.setObjectName("addBtn")
        add_btn.clicked.connect(self._add_interval)
        toolbar.addWidget(add_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "标题", "间隔", "活跃时段", "状态", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("alternate-background-color: #1a1a2e;")
        layout.addWidget(self.table)

    def _load_data(self):
        intervals = database.get_intervals()
        self.table.setRowCount(len(intervals))
        for row, iv in enumerate(intervals):
            self.table.setItem(row, 0, QTableWidgetItem(str(iv["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(iv["title"]))
            mins = iv["interval_minutes"]
            if mins >= 60 and mins % 60 == 0:
                self.table.setItem(row, 2, QTableWidgetItem(f"每{mins // 60}小时"))
            else:
                self.table.setItem(row, 2, QTableWidgetItem(f"每{mins}分钟"))
            start = iv.get("start_time", "")
            end = iv.get("end_time", "")
            self.table.setItem(row, 3, QTableWidgetItem(f"{start}-{end}" if start and end else "全天"))
            status_parts = []
            if not iv.get("enabled", 1):
                status_parts.append("⏸ 停用")
            elif iv.get("is_paused", 0):
                status_parts.append("⏸ 暂停中")
            else:
                status_parts.append("✅ 运行中")
            status_item = QTableWidgetItem(" ".join(status_parts))
            status_item.setForeground(QColor("#27ae60") if iv.get("enabled", 1) and not iv.get("is_paused", 0) else QColor("#e74c3c"))
            self.table.setItem(row, 4, status_item)

            ops_widget = QWidget()
            ops_layout = QHBoxLayout(ops_widget)
            ops_layout.setContentsMargins(4, 2, 4, 2)
            if iv.get("is_paused", 0) and iv.get("enabled", 1):
                resume_btn = QPushButton("▶")
                resume_btn.setFixedSize(30, 30)
                resume_btn.setToolTip("恢复")
                resume_btn.clicked.connect(lambda checked, iid=iv["id"]: self._resume_interval(iid))
                ops_layout.addWidget(resume_btn)
            elif iv.get("enabled", 1):
                pause_btn = QPushButton("⏸")
                pause_btn.setFixedSize(30, 30)
                pause_btn.setToolTip("暂停")
                pause_btn.clicked.connect(lambda checked, iid=iv["id"]: self._pause_interval(iid))
                ops_layout.addWidget(pause_btn)
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            edit_btn.setToolTip("编辑")
            edit_btn.clicked.connect(lambda checked, iid=iv["id"]: self._edit_interval(iid))
            ops_layout.addWidget(edit_btn)
            del_btn = QPushButton("🗑")
            del_btn.setFixedSize(30, 30)
            del_btn.setToolTip("删除")
            del_btn.clicked.connect(lambda checked, iid=iv["id"]: self._delete_interval(iid))
            ops_layout.addWidget(del_btn)
            ops_layout.addStretch()
            self.table.setCellWidget(row, 5, ops_widget)

    def _add_interval(self):
        dlg = AddIntervalDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            iid = database.add_interval(data)
            data["id"] = iid
            self.engine.add_interval_to_engine(data)
            self._load_data()

    def _edit_interval(self, iid):
        intervals = database.get_intervals()
        iv = None
        for i in intervals:
            if i["id"] == iid:
                iv = i
                break
        if not iv:
            return
        dlg = AddIntervalDialog(interval_data=iv, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            database.update_interval(iid, data)
            self.engine.remove_interval_from_engine(iid)
            data["id"] = iid
            self.engine.add_interval_to_engine(data)
            self._load_data()

    def _delete_interval(self, iid):
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除此间隔提醒吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.delete_interval(iid)
            self.engine.remove_interval_from_engine(iid)
            self._load_data()

    def _pause_interval(self, iid):
        self.engine.pause_interval(iid)
        self._load_data()

    def _resume_interval(self, iid):
        self.engine.resume_interval(iid)
        self._load_data()

    def refresh(self):
        self._load_data()


class HistoryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        toolbar = QHBoxLayout()
        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setDisplayFormat("yyyy-MM-dd")
        self.date_filter.setSpecialValueText("全部")
        self.date_filter.setDate(self.date_filter.minimumDate())
        self.date_filter.dateChanged.connect(self._load_data)
        toolbar.addWidget(QLabel("日期筛选："))
        toolbar.addWidget(self.date_filter)

        unread_only = QPushButton("未读")
        unread_only.setCheckable(True)
        unread_only.setObjectName("filterBtn")
        unread_only.toggled.connect(self._load_data)
        self.unread_btn = unread_only
        toolbar.addWidget(unread_only)

        mark_all_btn = QPushButton("✅ 全部已读")
        mark_all_btn.clicked.connect(self._mark_all_read)
        toolbar.addWidget(mark_all_btn)

        clear_btn = QPushButton("🗑 清空")
        clear_btn.clicked.connect(self._clear_history)
        toolbar.addWidget(clear_btn)

        export_btn = QPushButton("📥 导出CSV")
        export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(export_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "标题", "内容", "类型", "触发时间"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("alternate-background-color: #1a1a2e;")
        layout.addWidget(self.table)

    def _load_data(self):
        date_filter = None
        if self.date_filter.date() != self.date_filter.minimumDate():
            date_filter = self.date_filter.date().toString("yyyy-MM-dd")
        unread_only = self.unread_btn.isChecked()
        history = database.get_history(date_filter=date_filter, unread_only=unread_only)
        self.table.setRowCount(len(history))
        type_labels = {"timed": "定时", "countdown": "倒计时", "interval": "间隔", "hourly": "整点"}
        for row, h in enumerate(history):
            self.table.setItem(row, 0, QTableWidgetItem(str(h["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(h["title"]))
            self.table.setItem(row, 2, QTableWidgetItem(h.get("content", "")))
            self.table.setItem(row, 3, QTableWidgetItem(type_labels.get(h.get("reminder_type", ""), h.get("reminder_type", ""))))
            try:
                dt = datetime.fromisoformat(h["triggered_at"])
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                time_str = h.get("triggered_at", "")
            item = QTableWidgetItem(time_str)
            if not h.get("is_read", 1):
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor("#e94560"))
            self.table.setItem(row, 4, item)

    def _mark_all_read(self):
        database.mark_all_history_read()
        self._load_data()

    def _clear_history(self):
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有历史记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.clear_history()
            self._load_data()

    def _export_csv(self):
        from PyQt6.QtWidgets import QFileDialog
        import csv
        path, _ = QFileDialog.getSaveFileName(
            self, "导出历史记录", "reminders_history.csv", "CSV文件 (*.csv)"
        )
        if path:
            history = database.get_history()
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "标题", "内容", "类型", "触发时间", "已读"])
                for h in history:
                    writer.writerow([
                        h["id"], h["title"], h.get("content", ""),
                        h.get("reminder_type", ""), h.get("triggered_at", ""),
                        "是" if h.get("is_read", 1) else "否",
                    ])
            QMessageBox.information(self, "导出成功", f"历史记录已导出到：\n{path}")

    def refresh(self):
        self._load_data()


class MainWindow(QMainWindow):
    reminder_triggered_signal = pyqtSignal(dict)
    countdown_triggered_signal = pyqtSignal(dict)
    interval_triggered_signal = pyqtSignal(dict)
    hourly_chime_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("⏰ 多功能提醒工具")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        self.tray_manager = None

        self.audio = AudioManager(self)
        self.focus_mode = FocusModeManager(self)
        self.engine = ReminderEngine(self.audio, self.focus_mode, self)

        self._init_ui()
        self._connect_signals()
        self._start_status_timer()

    def closeEvent(self, event):
        if self.tray_manager:
            event.ignore()
            self.hide()
            if hasattr(self.tray_manager, 'tray'):
                self.tray_manager.tray.showMessage(
                    "已最小化到托盘",
                    "程序仍在后台运行，右键托盘图标可操作",
                    msecs=3000
                )
        else:
            event.accept()

    def _init_ui(self):
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        control_bar = QHBoxLayout()

        self.pause_btn = QPushButton("⏸️ 暂停所有提醒")
        self.pause_btn.setObjectName("pauseBtn")
        self.pause_btn.setCheckable(True)
        self.pause_btn.toggled.connect(self._toggle_pause)
        control_bar.addWidget(self.pause_btn)

        self.focus_btn = QPushButton("🧘 专注模式")
        self.focus_btn.setObjectName("focusBtn")
        self.focus_btn.setCheckable(True)
        self.focus_btn.setChecked(self.focus_mode.enabled)
        self.focus_btn.toggled.connect(self._toggle_focus)
        control_bar.addWidget(self.focus_btn)

        settings_btn = QPushButton("⚙️ 设置")
        settings_btn.clicked.connect(self._show_settings)
        control_bar.addWidget(settings_btn)

        control_bar.addStretch()

        self.next_reminder_label = QLabel("下一个提醒：计算中...")
        self.next_reminder_label.setStyleSheet("color: #a0a0b0; font-size: 12px;")
        control_bar.addWidget(self.next_reminder_label)

        layout.addLayout(control_bar)

        self.tabs = QTabWidget()
        self.reminder_tab = ReminderListTab(self.engine)
        self.countdown_tab = CountdownTab(self.engine)
        self.interval_tab = IntervalTab(self.engine)
        self.history_tab = HistoryTab()

        self.tabs.addTab(self.reminder_tab, "📋 定时提醒")
        self.tabs.addTab(self.countdown_tab, "⏱ 倒计时")
        self.tabs.addTab(self.interval_tab, "🔄 间隔提醒")
        self.tabs.addTab(self.history_tab, "📊 历史记录")

        layout.addWidget(self.tabs)

        self.statusBar().showMessage("就绪")

    def _connect_signals(self):
        self.engine.reminder_triggered.connect(self._on_reminder_triggered)
        self.engine.countdown_triggered.connect(self._on_countdown_triggered)
        self.engine.interval_triggered.connect(self._on_interval_triggered)
        self.engine.hourly_chime_triggered.connect(self._on_hourly_chime)
        self.focus_mode.focus_mode_changed.connect(self.focus_btn.setChecked)

    def _start_status_timer(self):
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(5000)
        self._update_status()

    def _update_status(self):
        r, t = self.engine.get_next_reminder()
        if r and t:
            delta = t - datetime.now()
            if delta.total_seconds() > 0:
                hours, remainder = divmod(int(delta.total_seconds()), 3600)
                mins, secs = divmod(remainder, 60)
                if hours > 0:
                    time_str = f"{hours}小时{mins}分钟后"
                else:
                    time_str = f"{mins}分钟后"
                self.next_reminder_label.setText(f"下一个提醒：{r['title']}（{time_str}）")
            else:
                self.next_reminder_label.setText("下一个提醒：即将触发")
        else:
            self.next_reminder_label.setText("下一个提醒：无")

        paused = self.engine.is_paused()
        focus = self.focus_mode.is_active()
        status_parts = []
        if paused:
            status_parts.append("⏸ 提醒已暂停")
        if focus:
            status_parts.append("🧘 专注模式")
        if not status_parts:
            status_parts.append("✅ 运行中")
        self.statusBar().showMessage(" | ".join(status_parts))

    def _toggle_pause(self, checked):
        self.engine.set_paused(checked)
        if checked:
            self.pause_btn.setText("▶️ 恢复所有提醒")
        else:
            self.pause_btn.setText("⏸️ 暂停所有提醒")
        self._update_status()

    def _toggle_focus(self, checked):
        self.focus_mode.set_enabled(checked)
        self._update_status()

    def _show_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.focus_mode._load_settings()
            self._update_status()

    def _on_reminder_triggered(self, data):
        popup = NotificationPopup(data["title"], data.get("content", ""), self)
        popup.show_at_bottom_right()
        self.reminder_tab.refresh()
        self.history_tab.refresh()
        self._update_status()
        self.reminder_triggered_signal.emit(data)

    def _on_countdown_triggered(self, data):
        popup = NotificationPopup(f"⏱ 倒计时结束", data["title"], self)
        popup.show_at_bottom_right()
        self.history_tab.refresh()
        self.countdown_triggered_signal.emit(data)

    def _on_interval_triggered(self, data):
        popup = NotificationPopup(f"🔄 {data['title']}", data.get("content", ""), self)
        popup.show_at_bottom_right()
        self.history_tab.refresh()
        self.interval_triggered_signal.emit(data)

    def _on_hourly_chime(self):
        now = datetime.now()
        self.statusBar().showMessage(f"🔔 整点报时：{now.hour}点整", 5000)
        self.hourly_chime_signal.emit()
