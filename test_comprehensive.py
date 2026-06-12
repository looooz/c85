import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database


class TestDatabaseFull(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.test_db.close()
        database.DB_PATH = cls.test_db.name
        database.init_db()

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.test_db.name)

    def test_reminder_crud_complete(self):
        data = {
            "title": "完整CRUD测试",
            "content": "测试内容",
            "reminder_type": "daily",
            "trigger_time": datetime.now().isoformat(),
            "advance_minutes": 10,
            "enabled": True,
            "sound_type": "chime",
            "volume": 75,
        }
        rid = database.add_reminder(data)
        self.assertGreater(rid, 0)

        r = database.get_reminder_by_id(rid)
        self.assertEqual(r["title"], "完整CRUD测试")
        self.assertEqual(r["content"], "测试内容")
        self.assertEqual(r["reminder_type"], "daily")
        self.assertEqual(r["advance_minutes"], 10)
        self.assertEqual(r["sound_type"], "chime")
        self.assertEqual(r["volume"], 75)

        database.update_reminder(rid, {"title": "更新后的标题", "enabled": False})
        r = database.get_reminder_by_id(rid)
        self.assertEqual(r["title"], "更新后的标题")
        self.assertEqual(r["enabled"], 0)

        all_reminders = database.get_reminders()
        self.assertGreaterEqual(len(all_reminders), 1)

        database.delete_reminder(rid)
        r = database.get_reminder_by_id(rid)
        self.assertIsNone(r)

    def test_reminder_all_types(self):
        types = ["single", "daily", "weekly", "monthly", "yearly"]
        for rtype in types:
            data = {
                "title": f"测试{rtype}提醒",
                "reminder_type": rtype,
                "trigger_time": datetime.now().isoformat(),
                "enabled": True,
            }
            if rtype == "weekly":
                data["week_day"] = 3
            if rtype == "monthly":
                data["month_day"] = 20
            rid = database.add_reminder(data)
            r = database.get_reminder_by_id(rid)
            self.assertEqual(r["reminder_type"], rtype)

    def test_reminder_enabled_filter(self):
        database.add_reminder({
            "title": "启用的提醒",
            "reminder_type": "single",
            "trigger_time": datetime.now().isoformat(),
            "enabled": True,
        })
        database.add_reminder({
            "title": "禁用的提醒",
            "reminder_type": "single",
            "trigger_time": datetime.now().isoformat(),
            "enabled": False,
        })
        all_r = database.get_reminders()
        enabled_r = database.get_reminders(enabled_only=True)
        self.assertGreater(len(all_r), len(enabled_r))

    def test_countdown_crud(self):
        data = {
            "title": "测试倒计时",
            "duration_seconds": 300,
        }
        cid = database.add_countdown(data)
        self.assertGreater(cid, 0)

        cds = database.get_countdowns()
        self.assertGreaterEqual(len(cds), 1)

        database.update_countdown(cid, {"remaining_seconds": 150, "is_running": 0})
        cds = database.get_countdowns()
        cd = next((c for c in cds if c["id"] == cid), None)
        self.assertEqual(cd["remaining_seconds"], 150)
        self.assertEqual(cd["is_running"], 0)

        active_cds = database.get_countdowns(active_only=True)
        self.assertIn(cid, [c["id"] for c in active_cds])

        database.update_countdown(cid, {"triggered": 1})
        active_cds = database.get_countdowns(active_only=True)
        self.assertNotIn(cid, [c["id"] for c in active_cds])

        database.delete_countdown(cid)
        cds = database.get_countdowns()
        self.assertNotIn(cid, [c["id"] for c in cds])

    def test_interval_crud(self):
        data = {
            "title": "测试间隔提醒",
            "content": "间隔内容",
            "interval_minutes": 30,
            "start_time": "09:00",
            "end_time": "18:00",
            "enabled": True,
            "sound_type": "ding",
            "volume": 70,
        }
        iid = database.add_interval(data)
        self.assertGreater(iid, 0)

        ivs = database.get_intervals()
        self.assertGreaterEqual(len(ivs), 1)

        database.update_interval(iid, {"title": "更新的间隔", "is_paused": True})
        ivs = database.get_intervals()
        iv = next((i for i in ivs if i["id"] == iid), None)
        self.assertEqual(iv["title"], "更新的间隔")
        self.assertEqual(iv["is_paused"], 1)

        database.delete_interval(iid)
        ivs = database.get_intervals()
        self.assertNotIn(iid, [i["id"] for i in ivs])

    def test_history_crud(self):
        data = {
            "title": "测试历史",
            "content": "历史内容",
            "reminder_type": "timed",
            "triggered_at": datetime.now().isoformat(),
        }
        hid = database.add_history(data)
        self.assertGreater(hid, 0)

        history = database.get_history()
        self.assertGreaterEqual(len(history), 1)

        database.mark_history_read(hid)
        history = database.get_history(unread_only=True)
        self.assertNotIn(hid, [h["id"] for h in history])

        database.add_history({
            "title": "未读历史",
            "reminder_type": "countdown",
        })
        unread = database.get_history(unread_only=True)
        self.assertGreaterEqual(len(unread), 1)

        database.mark_all_history_read()
        unread = database.get_history(unread_only=True)
        self.assertEqual(len(unread), 0)

        today = datetime.now().strftime("%Y-%m-%d")
        today_history = database.get_history(date_filter=today)
        self.assertGreaterEqual(len(today_history), 1)

        all_count = len(database.get_history())
        database.delete_history(hid)
        after_delete = database.get_history()
        self.assertEqual(len(after_delete), all_count - 1)

        database.clear_history()
        self.assertEqual(len(database.get_history()), 0)

    def test_settings_all(self):
        settings = database.get_all_settings()
        expected_keys = [
            "hourly_chime_enabled", "hourly_chime_start", "hourly_chime_end",
            "hourly_chime_sound", "focus_mode_enabled", "focus_mode_start",
            "focus_mode_end", "whitelist_fullscreen", "default_sound",
            "default_volume", "tts_enabled", "theme"
        ]
        for key in expected_keys:
            self.assertIn(key, settings)

        database.set_setting("test_custom", "custom_value")
        self.assertEqual(database.get_setting("test_custom"), "custom_value")

        default_val = database.get_setting("nonexistent", "fallback")
        self.assertEqual(default_val, "fallback")

    def test_reminder_last_triggered(self):
        rid = database.add_reminder({
            "title": "触发时间测试",
            "reminder_type": "single",
            "trigger_time": datetime.now().isoformat(),
        })
        trigger_time = datetime.now().isoformat()
        database.update_reminder_last_triggered(rid, trigger_time)
        r = database.get_reminder_by_id(rid)
        self.assertEqual(r["last_triggered"], trigger_time)


class TestCoreFunctionality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.test_db.close()
        database.DB_PATH = cls.test_db.name
        database.init_db()

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.test_db.name)

    def test_audio_manager_sound_generation(self):
        from core import AudioManager, generate_default_sounds, SOUNDS_DIR
        sounds_dir = generate_default_sounds()
        self.assertTrue(os.path.exists(sounds_dir))
        
        expected_sounds = ["default.wav", "chime.wav", "ding.wav", "alert.wav", "gentle.wav"]
        for s in expected_sounds:
            self.assertTrue(os.path.exists(os.path.join(sounds_dir, s)))

    def test_audio_manager_available_sounds(self):
        from core import AudioManager
        from PyQt6.QtCore import QObject
        parent = QObject()
        audio = AudioManager(parent)
        available = audio.get_available_sounds()
        self.assertIn("default", available)
        self.assertIn("chime", available)

    def test_focus_mode_manager(self):
        from core import FocusModeManager
        from PyQt6.QtCore import QObject
        
        parent = QObject()
        focus = FocusModeManager(parent)
        
        focus.set_enabled(True)
        self.assertTrue(focus.enabled)
        self.assertTrue(focus.is_active())
        
        focus.set_enabled(False)
        self.assertFalse(focus.enabled)
        self.assertFalse(focus.is_active())
        
        focus.set_time_range("09:00", "18:00")
        self.assertEqual(focus.start_time, "09:00")
        self.assertEqual(focus.end_time, "18:00")
        
        focus.set_whitelist_fullscreen(False)
        self.assertFalse(focus.whitelist_fullscreen)

    def test_theme_manager(self):
        from theme import ThemeManager, THEMES
        from PyQt6.QtCore import QObject
        
        parent = QObject()
        tm = ThemeManager(parent)
        
        themes = tm.get_all_themes()
        self.assertEqual(len(themes), 2)
        self.assertIn(("dark", "深色主题"), themes)
        self.assertIn(("light", "浅色主题"), themes)
        
        current = tm.get_current_theme()
        self.assertIn(current, THEMES)
        
        theme = tm.get_theme()
        self.assertIn("name", theme)
        self.assertIn("bg_main", theme)
        self.assertIn("text_primary", theme)
        
        stylesheet = tm.get_stylesheet()
        self.assertIsInstance(stylesheet, str)
        self.assertGreater(len(stylesheet), 0)

    def test_reminder_engine_next_reminder_calculation(self):
        from core import ReminderEngine, AudioManager, FocusModeManager
        from PyQt6.QtCore import QObject
        
        parent = QObject()
        audio = AudioManager(parent)
        focus = FocusModeManager(parent)
        engine = ReminderEngine(audio, focus, parent)
        
        future_time = datetime.now() + timedelta(hours=1)
        rid = database.add_reminder({
            "title": "下一个提醒测试",
            "reminder_type": "single",
            "trigger_time": future_time.isoformat(),
            "enabled": True,
        })
        
        reminder, next_time = engine.get_next_reminder()
        self.assertIsNotNone(reminder)
        self.assertIsNotNone(next_time)
        self.assertEqual(reminder["id"], rid)
        self.assertGreater(next_time, datetime.now())

    def test_reminder_engine_pause(self):
        from core import ReminderEngine, AudioManager, FocusModeManager
        from PyQt6.QtCore import QObject
        
        parent = QObject()
        audio = AudioManager(parent)
        focus = FocusModeManager(parent)
        engine = ReminderEngine(audio, focus, parent)
        
        self.assertFalse(engine.is_paused())
        engine.set_paused(True)
        self.assertTrue(engine.is_paused())
        engine.set_paused(False)
        self.assertFalse(engine.is_paused())

    def test_reminder_trigger_logic_single(self):
        from core import ReminderEngine
        now = datetime.now()
        
        r_single = {
            "id": 1,
            "title": "单次提醒",
            "reminder_type": "single",
            "trigger_time": now.isoformat(),
            "advance_minutes": 0,
            "last_triggered": None,
            "enabled": 1,
        }
        
        engine_module = sys.modules['core']
        should_trigger = getattr(ReminderEngine, '_should_trigger')
        result = should_trigger(None, r_single, now)
        self.assertTrue(result)

    def test_reminder_trigger_logic_daily(self):
        from core import ReminderEngine
        now = datetime.now().replace(second=0, microsecond=0)
        
        r_daily = {
            "id": 2,
            "title": "每日提醒",
            "reminder_type": "daily",
            "trigger_time": now.isoformat(),
            "advance_minutes": 0,
            "last_triggered": None,
            "enabled": 1,
        }
        
        engine_module = sys.modules['core']
        should_trigger = getattr(ReminderEngine, '_should_trigger')
        result = should_trigger(None, r_daily, now)
        self.assertTrue(result)
        
        now_future = now + timedelta(seconds=5)
        result = should_trigger(None, r_daily, now_future)
        self.assertFalse(result)

    def test_reminder_trigger_with_advance(self):
        from core import ReminderEngine
        now = datetime.now()
        future = now + timedelta(minutes=5)
        
        r_advance = {
            "id": 3,
            "title": "提前提醒",
            "reminder_type": "single",
            "trigger_time": future.isoformat(),
            "advance_minutes": 5,
            "last_triggered": None,
            "enabled": 1,
        }
        
        engine_module = sys.modules['core']
        should_trigger = getattr(ReminderEngine, '_should_trigger')
        result = should_trigger(None, r_advance, now)
        self.assertTrue(result)

    def test_reminder_not_trigger_duplicate(self):
        from core import ReminderEngine
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        r_daily = {
            "id": 4,
            "title": "重复检查",
            "reminder_type": "daily",
            "trigger_time": now.isoformat(),
            "advance_minutes": 0,
            "last_triggered": today_str + "T09:00:00",
            "enabled": 1,
        }
        
        engine_module = sys.modules['core']
        should_trigger = getattr(ReminderEngine, '_should_trigger')
        result = should_trigger(None, r_daily, now)
        self.assertFalse(result)


class TestUITextBased(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.test_db.close()
        database.DB_PATH = cls.test_db.name
        database.init_db()

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.test_db.name)

    def test_dialog_data_validation_reminder(self):
        from ui_dialogs import AddReminderDialog
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QDateTime
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        dlg = AddReminderDialog()
        dlg.title_edit.setText("测试提醒")
        
        data = dlg.get_data()
        self.assertEqual(data["title"], "测试提醒")
        self.assertIn(data["reminder_type"], ["single", "daily", "weekly", "monthly", "yearly"])
        self.assertIn(data["sound_type"], ["default", "chime", "ding", "alert", "gentle"])
        self.assertGreaterEqual(data["volume"], 0)
        self.assertLessEqual(data["volume"], 100)
        
        dlg.close()

    def test_dialog_data_validation_countdown(self):
        from ui_dialogs import AddCountdownDialog
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        dlg = AddCountdownDialog()
        dlg.title_edit.setText("番茄钟")
        dlg.minutes_spin.setValue(25)
        dlg.seconds_spin.setValue(0)
        
        data = dlg.get_data()
        self.assertEqual(data["title"], "番茄钟")
        self.assertEqual(data["duration_seconds"], 1500)
        
        dlg.close()

    def test_dialog_data_validation_interval(self):
        from ui_dialogs import AddIntervalDialog
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        dlg = AddIntervalDialog()
        dlg.title_edit.setText("喝水提醒")
        dlg.interval_value.setValue(30)
        dlg.interval_unit.setCurrentIndex(0)
        
        data = dlg.get_data()
        self.assertEqual(data["title"], "喝水提醒")
        self.assertEqual(data["interval_minutes"], 30)
        
        dlg.interval_unit.setCurrentIndex(1)
        data = dlg.get_data()
        self.assertEqual(data["interval_minutes"], 1800)
        
        dlg.close()

    def test_settings_dialog_defaults(self):
        from ui_dialogs import SettingsDialog
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        dlg = SettingsDialog()
        
        self.assertIsInstance(dlg.chime_enabled.isChecked(), bool)
        self.assertGreaterEqual(dlg.chime_start.value(), 0)
        self.assertLessEqual(dlg.chime_start.value(), 23)
        self.assertGreaterEqual(dlg.chime_end.value(), 0)
        self.assertLessEqual(dlg.chime_end.value(), 23)
        
        dlg.close()

    def test_reminder_list_tab_data_loading(self):
        from PyQt6.QtWidgets import QApplication
        from ui_main import ReminderListTab
        from core import ReminderEngine, AudioManager, FocusModeManager
        from PyQt6.QtCore import QObject
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        database.add_reminder({
            "title": "界面测试提醒",
            "reminder_type": "daily",
            "trigger_time": datetime.now().isoformat(),
            "enabled": True,
        })
        
        parent = QObject()
        audio = AudioManager(parent)
        focus = FocusModeManager(parent)
        engine = ReminderEngine(audio, focus, parent)
        
        tab = ReminderListTab(engine)
        tab._load_data()
        
        self.assertGreater(tab.table.rowCount(), 0)
        self.assertEqual(tab.table.columnCount(), 6)


def run_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseFull))
    suite.addTests(loader.loadTestsFromTestCase(TestCoreFunctionality))
    suite.addTests(loader.loadTestsFromTestCase(TestUITextBased))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
