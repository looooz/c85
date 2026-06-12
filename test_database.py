import os
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database


class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.test_db.close()
        database.DB_PATH = cls.test_db.name
        database.init_db()

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.test_db.name)

    def test_01_init_db_creates_tables(self):
        conn = database.get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        conn.close()
        self.assertIn("reminders", tables)
        self.assertIn("countdowns", tables)
        self.assertIn("intervals", tables)
        self.assertIn("history", tables)
        self.assertIn("settings", tables)

    def test_02_init_db_sets_default_settings(self):
        settings = database.get_all_settings()
        self.assertEqual(settings["hourly_chime_enabled"], "0")
        self.assertEqual(settings["hourly_chime_start"], "9")
        self.assertEqual(settings["hourly_chime_end"], "21")
        self.assertEqual(settings["hourly_chime_sound"], "chime")
        self.assertEqual(settings["focus_mode_enabled"], "0")
        self.assertEqual(settings["whitelist_fullscreen"], "1")
        self.assertEqual(settings["default_sound"], "default")
        self.assertEqual(settings["default_volume"], "80")
        self.assertEqual(settings["tts_enabled"], "0")
        self.assertEqual(settings["theme"], "dark")

    def test_03_get_setting_default(self):
        val = database.get_setting("nonexistent_key", "default_val")
        self.assertEqual(val, "default_val")

    def test_04_set_and_get_setting(self):
        database.set_setting("test_key", "test_value")
        val = database.get_setting("test_key")
        self.assertEqual(val, "test_value")

    def test_05_add_reminder_single(self):
        data = {
            "title": "测试单次提醒",
            "content": "提醒内容",
            "reminder_type": "single",
            "trigger_time": datetime.now().isoformat(),
            "advance_minutes": 5,
            "enabled": True,
            "sound_type": "default",
            "volume": 80,
        }
        rid = database.add_reminder(data)
        self.assertGreater(rid, 0)
        r = database.get_reminder_by_id(rid)
        self.assertEqual(r["title"], "测试单次提醒")
        self.assertEqual(r["reminder_type"], "single")
        self.assertEqual(r["advance_minutes"], 5)
        self.assertEqual(r["enabled"], 1)

    def test_06_add_reminder_weekly(self):
        data = {
            "title": "测试每周提醒",
            "reminder_type": "weekly",
            "trigger_time": datetime.now().isoformat(),
            "week_day": 2,
            "enabled": True,
        }
        rid = database.add_reminder(data)
        r = database.get_reminder_by_id(rid)
        self.assertEqual(r["reminder_type"], "weekly")
        self.assertEqual(r["week_day"], 2)

    def test_07_add_reminder_monthly(self):
        data = {
            "title": "测试每月提醒",
            "reminder_type": "monthly",
            "trigger_time": datetime.now().isoformat(),
            "month_day": 15,
            "enabled": True,
        }
        rid = database.add_reminder(data)
        r = database.get_reminder_by_id(rid)
        self.assertEqual(r["reminder_type"], "monthly")
        self.assertEqual(r["month_day"], 15)

    def test_08_update_reminder(self):
        data = {
            "title": "待更新提醒",
            "reminder_type": "daily",
            "trigger_time": datetime.now().isoformat(),
            "enabled": True,
        }
        rid = database.add_reminder(data)
        database.update_reminder(rid, {"title": "已更新提醒", "enabled": False})
        r = database.get_reminder_by_id(rid)
        self.assertEqual(r["title"], "已更新提醒")
        self.assertEqual(r["enabled"], 0)

    def test_09_delete_reminder(self):
        data = {
            "title": "待删除提醒",
            "reminder_type": "single",
            "trigger_time": datetime.now().isoformat(),
        }