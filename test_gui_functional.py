import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

os.environ['QT_QPA_PLATFORM'] = 'offscreen'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database


class TestGUIFunctional(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.test_db.close()
        database.DB_PATH = cls.test_db.name
        database.init_db()
        
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        import theme
        theme._theme_instance = None

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.test_db.name)

    def test_01_main_window_initialization(self):
        from ui_main import MainWindow
        
        window = MainWindow()
        self.assertIsNotNone(window)
        self.assertEqual(window.windowTitle(), "⏰ 多功能提醒工具")
        self.assertGreaterEqual(window.width(), 800)
        self.assertGreaterEqual(window.height(), 600)
        
        self.assertIsNotNone(window.reminder_tab)
        self.assertIsNotNone(window.countdown_tab)
        self.assertIsNotNone(window.interval_tab)
        self.assertIsNotNone(window.history_tab)
        
        self.assertIsNotNone(window.engine)
        self.assertIsNotNone(window.audio)
        self.assertIsNotNone(window.focus_mode)
        
        self.assertIsNotNone(window.tabs)
        self.assertEqual(window.tabs.count(), 4)
        
        window.close()

    def test_02_reminder_tab_ui(self):
        from ui_main import ReminderListTab
        from core import ReminderEngine, AudioManager, FocusModeManager
        from PyQt6.QtCore import QObject
        
        parent = QObject()
        audio = AudioManager(parent)
        focus = FocusModeManager(parent)
        engine = ReminderEngine(audio, focus, parent)
        
        tab = ReminderListTab(engine)
        self.assertIsNotNone(tab.table)
        self.assertEqual(tab.table.columnCount(), 6)
        
        headers = ["序号", "标题", "类型", "触发时间", "提前", "状态"]
        for i, header in enumerate(headers):
            self.assertEqual(tab.table.horizontalHeaderItem(i).text(), header)
        
        rid = database.add_reminder({
            "title": "UI测试提醒",
            "reminder_type": "daily",
            "trigger_time": datetime.now().isoformat(),
            "enabled": True,
        })
        
        tab._load_data()
        self.assertGreater(tab.table.rowCount(), 0)
        
        found = False
        for row in range(tab.table.rowCount()):
            item = tab.table.item(row, 1)
            if item and item.text() == "UI测试提醒":
                found = True
                break
        self.assertTrue(found)

    def test_03_countdown_tab_ui(self):
        from ui_main import CountdownTab
        from core import ReminderEngine, AudioManager, FocusModeManager
        from PyQt6.QtCore import QObject
        
        parent = QObject()
        audio = AudioManager(parent)
        focus = FocusModeManager(parent)
        engine = ReminderEngine(audio, focus, parent)
        
        tab = CountdownTab(engine)
        
        cid = database.add_countdown({
            "title": "UI测试倒计时",
            "duration_seconds": 300,
        })
        engine.start_countdown(cid, 300)
        
        tab._load_data()
        self.assertGreater(tab.scroll_layout.count(), 0)

    def test_04_interval_tab_ui(self):
        from ui_main import IntervalTab
        from core import ReminderEngine, AudioManager, FocusModeManager
        from PyQt6.QtCore import QObject
        
        parent = QObject()
        audio = AudioManager(parent)
        focus = FocusModeManager(parent)
        engine = ReminderEngine(audio, focus, parent)
        
        tab = IntervalTab(engine)
        self.assertEqual(tab.table.columnCount(), 6)
        
        iid = database.add_interval({
            "title": "UI测试间隔",
            "interval_minutes": 30,
            "enabled": True,
        })
        
        iv_data = database.get_intervals()
        iv = next((i for i in iv_data if i["id"] == iid), None)
        engine.add_interval_to_engine(iv)
        
        tab._load_data()
        self.assertGreater(tab.table.rowCount(), 0)

    def test_05_history_tab_ui(self):
        from ui_main import HistoryTab
        
        tab = HistoryTab()
        self.assertEqual(tab.table.columnCount(), 5)
        
        database.add_history({
            "title": "UI测试历史",
            "content": "历史内容",
            "reminder_type": "timed",
        })
        
        tab._load_data()
        self.assertGreater(tab.table.rowCount(), 0)

    def test_06_add_reminder_dialog_all_types(self):
        from ui_dialogs import AddReminderDialog
        from PyQt6.QtCore import QDateTime
        
        types = ["single", "daily", "weekly", "monthly", "yearly"]
        type_indices = {"single": 0, "daily": 1, "weekly": 2, "monthly": 3, "yearly": 4}
        
        for rtype, idx in type_indices.items():
            dlg = AddReminderDialog()
            dlg.title_edit.setText(f"测试{rtype}提醒")
            dlg.type_combo.setCurrentIndex(idx)
            
            if rtype == "weekly":
                dlg.week_combo.setCurrentIndex(2)
            if rtype == "monthly":
                dlg.month_spin.setValue(15)
            
            data = dlg.get_data()
            self.assertEqual(data["reminder_type"], rtype)
            self.assertGreater(len(data["title"]), 0)
            dlg.close()

    def test_07_add_reminder_dialog_sound_settings(self):
        from ui_dialogs import AddReminderDialog
        
        dlg = AddReminderDialog()
        dlg.title_edit.setText("音效测试")
        
        dlg.sound_combo.setCurrentIndex(1)
        dlg.volume_slider.setValue(50)
        
        data = dlg.get_data()
        self.assertEqual(data["sound_type"], "chime")
        self.assertEqual(data["volume"], 50)
        dlg.close()

    def test_08_add_countdown_dialog(self):
        from ui_dialogs import AddCountdownDialog
        
        dlg = AddCountdownDialog()
        dlg.title_edit.setText("番茄钟测试")
        dlg.hours_spin.setValue(1)
        dlg.minutes_spin.setValue(30)
        dlg.seconds_spin.setValue(45)
        
        data = dlg.get_data()
        self.assertEqual(data["title"], "番茄钟测试")
        self.assertEqual(data["duration_seconds"], 5445)
        dlg.close()

    def test_09_add_interval_dialog(self):
        from ui_dialogs import AddIntervalDialog
        from PyQt6.QtCore import QTime
        
        dlg = AddIntervalDialog()
        dlg.title_edit.setText("喝水提醒")
        dlg.interval_value.setValue(1)
        dlg.interval_unit.setCurrentIndex(1)
        dlg.start_time.setTime(QTime(9, 0))
        dlg.end_time.setTime(QTime(18, 0))
        
        data = dlg.get_data()
        self.assertEqual(data["title"], "喝水提醒")
        self.assertEqual(data["interval_minutes"], 60)
        self.assertEqual(data["start_time"], "09:00")
        self.assertEqual(data["end_time"], "18:00")
        dlg.close()

    def test_10_settings_dialog(self):
        from ui_dialogs import SettingsDialog
        
        dlg = SettingsDialog()
        
        dlg.chime_enabled.setChecked(True)
        dlg.chime_start.setValue(8)
        dlg.chime_end.setValue(22)
        dlg.chime_sound.setCurrentIndex(2)
        dlg.tts_enabled.setChecked(True)
        dlg.focus_enabled.setChecked(True)
        
        themes = dlg.theme_manager.get_all_themes()
        for i in range(dlg.theme_combo.count()):
            self.assertIn(dlg.theme_combo.itemText(i), [t[1] for t in themes])
        
        dlg.close()

    def test_11_theme_manager_dark_light(self):
        from theme import ThemeManager, THEMES
        from PyQt6.QtCore import QObject
        
        parent = QObject()
        tm = ThemeManager(parent)
        
        tm.set_theme("dark")
        self.assertEqual(tm.get_current_theme(), "dark")
        dark_theme = tm.get_theme()
        self.assertEqual(dark_theme["name"], "dark")
        self.assertIn("#1a1a2e", dark_theme["bg_main"])
        
        tm.set_theme("light")
        self.assertEqual(tm.get_current_theme(), "light")
        light_theme = tm.get_theme()
        self.assertEqual(light_theme["name"], "light")
        self.assertIn("#f5f7fa", light_theme["bg_main"])

    def test_12_stylesheet_generation(self):
        from theme import ThemeManager
        from PyQt6.QtCore import QObject
        
        parent = QObject()
        tm = ThemeManager(parent)
        
        tm.set_theme("dark")
        dark_ss = tm.get_stylesheet()
        self.assertIn("QMainWindow", dark_ss)
        self.assertIn("QPushButton", dark_ss)
        self.assertIn("QTableWidget", dark_ss)
        
        tm.set_theme("light")
        light_ss = tm.get_stylesheet()
        self.assertIn("QMainWindow", light_ss)
        self.assertIn("QPushButton", light_ss)
        self.assertIn("QTableWidget", light_ss)
        
        self.assertNotEqual(dark_ss, light_ss)

    def test_13_notification_popup(self):
        from ui_dialogs import NotificationPopup
        from PyQt6.QtWidgets import QApplication
        
        popup = NotificationPopup("测试标题", "测试内容")
        self.assertEqual(popup.title_label.text(), "🔔 测试标题")
        self.assertIsNotNone(popup.content_label)
        self.assertEqual(popup.content_label.text(), "测试内容")
        popup.close()

    def test_14_tray_icon_generation(self):
        from tray import create_tray_icon
        from PyQt6.QtGui import QIcon
        
        icon = create_tray_icon()
        self.assertIsInstance(icon, QIcon)
        self.assertFalse(icon.isNull())

    def test_15_main_window_status_bar(self):
        from ui_main import MainWindow
        
        window = MainWindow()
        self.assertIsNotNone(window.statusBar())
        self.assertIsNotNone(window.next_reminder_label)
        
        window._update_status()
        status_text = window.statusBar().currentMessage()
        self.assertIn(status_text, ["✅ 运行中", "⏸ 提醒已暂停", "🧘 专注模式"])
        
        window.close()

    def test_16_focus_mode_integration(self):
        from ui_main import MainWindow
        
        window = MainWindow()
        self.assertIsNotNone(window.focus_btn)
        self.assertIsNotNone(window.focus_mode)
        
        window.focus_mode.set_enabled(True)
        self.assertTrue(window.focus_mode.is_active())
        self.assertTrue(window.focus_btn.isChecked())
        
        window._update_status()
        status_text = window.statusBar().currentMessage()
        self.assertIn("🧘 专注模式", status_text)
        
        window.focus_mode.set_enabled(False)
        self.assertFalse(window.focus_mode.is_active())
        
        window.close()

    def test_17_pause_all_integration(self):
        from ui_main import MainWindow
        
        window = MainWindow()
        self.assertIsNotNone(window.pause_btn)
        self.assertIsNotNone(window.engine)
        
        window.pause_btn.setChecked(True)
        self.assertTrue(window.engine.is_paused())
        
        window._update_status()
        status_text = window.statusBar().currentMessage()
        self.assertIn("⏸ 提醒已暂停", status_text)
        
        window.pause_btn.setChecked(False)
        self.assertFalse(window.engine.is_paused())
        
        window.close()

    def test_18_tab_navigation(self):
        from ui_main import MainWindow
        
        window = MainWindow()
        self.assertEqual(window.tabs.currentIndex(), 0)
        
        window.tabs.setCurrentIndex(1)
        self.assertEqual(window.tabs.currentIndex(), 1)
        self.assertEqual(window.tabs.tabText(1), "⏱ 倒计时")
        
        window.tabs.setCurrentIndex(2)
        self.assertEqual(window.tabs.currentIndex(), 2)
        self.assertEqual(window.tabs.tabText(2), "🔄 间隔提醒")
        
        window.tabs.setCurrentIndex(3)
        self.assertEqual(window.tabs.currentIndex(), 3)
        self.assertEqual(window.tabs.tabText(3), "📊 历史记录")
        
        window.close()

    def test_19_history_export_function(self):
        from ui_main import HistoryTab
        
        tab = HistoryTab()
        
        database.add_history({
            "title": "导出测试1",
            "content": "内容1",
            "reminder_type": "timed",
        })
        database.add_history({
            "title": "导出测试2",
            "content": "内容2",
            "reminder_type": "countdown",
        })
        
        tab._load_data()
        self.assertGreaterEqual(tab.table.rowCount(), 2)
        
        import csv
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig') as f:
            path = f.name
        
        try:
            history = database.get_history()
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "标题", "内容", "类型", "触发时间", "已读"])
                for h in history:
                    writer.writerow([
                        h["id"], h["title"], h.get("content", ""),
                        h.get("reminder_type", ""), h.get("triggered_at", ""),
                        "是" if h.get("is_read", 1) else "否",
                    ])
            
            self.assertTrue(os.path.exists(path))
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                rows = list(reader)
            self.assertGreater(len(rows), 1)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_20_dialog_edit_mode(self):
        from ui_dialogs import AddReminderDialog, AddIntervalDialog
        
        reminder_data = {
            "id": 1,
            "title": "待编辑提醒",
            "content": "原内容",
            "reminder_type": "weekly",
            "trigger_time": datetime.now().isoformat(),
            "week_day": 2,
            "advance_minutes": 5,
            "enabled": True,
            "sound_type": "chime",
            "volume": 75,
        }
        
        dlg = AddReminderDialog(reminder_data=reminder_data)
        self.assertEqual(dlg.title_edit.text(), "待编辑提醒")
        self.assertEqual(dlg.content_edit.toPlainText(), "原内容")
        self.assertEqual(dlg.type_combo.currentIndex(), 2)
        self.assertEqual(dlg.week_combo.currentIndex(), 2)
        self.assertEqual(dlg.advance_combo.currentIndex(), 1)
        self.assertTrue(dlg.enabled_check.isChecked())
        self.assertEqual(dlg.sound_combo.currentIndex(), 1)
        self.assertEqual(dlg.volume_slider.value(), 75)
        dlg.close()
        
        interval_data = {
            "id": 1,
            "title": "待编辑间隔",
            "content": "间隔内容",
            "interval_minutes": 120,
            "start_time": "09:00",
            "end_time": "18:00",
            "enabled": True,
            "sound_type": "ding",
            "volume": 60,
        }
        
        dlg2 = AddIntervalDialog(interval_data=interval_data)
        self.assertEqual(dlg2.title_edit.text(), "待编辑间隔")
        self.assertEqual(dlg2.interval_value.value(), 2)
        self.assertEqual(dlg2.interval_unit.currentIndex(), 1)
        self.assertTrue(dlg2.enabled_check.isChecked())
        self.assertEqual(dlg2.sound_combo.currentIndex(), 2)
        self.assertEqual(dlg2.volume_slider.value(), 60)
        dlg2.close()


def run_gui_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestGUIFunctional))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    result = run_gui_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
