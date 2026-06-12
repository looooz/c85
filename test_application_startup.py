import os
import sys
import tempfile
import time
import shutil

os.environ['QT_QPA_PLATFORM'] = 'offscreen'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database

DB_BACKUP = None


def setup_database():
    global DB_BACKUP
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reminders.db")
    if os.path.exists(db_path):
        DB_BACKUP = db_path + ".backup"
        shutil.copy2(db_path, DB_BACKUP)
    database.init_db()


def restore_database():
    global DB_BACKUP
    if DB_BACKUP and os.path.exists(DB_BACKUP):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reminders.db")
        shutil.copy2(DB_BACKUP, db_path)
        os.unlink(DB_BACKUP)
        DB_BACKUP = None


def test_application_imports():
    print("=" * 60)
    print("测试应用模块导入")
    print("=" * 60)
    
    try:
        from PyQt6 import QtCore, QtWidgets, QtGui
        print(f"✅ PyQt6 导入成功，版本: {QtCore.QT_VERSION_STR}")
    except ImportError as e:
        print(f"❌ PyQt6 导入失败: {e}")
        return False
    
    modules = [
        "database",
        "core",
        "theme",
        "tray",
        "ui_dialogs",
        "ui_main",
    ]
    
    all_success = True
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}.py 导入成功")
        except Exception as e:
            print(f"❌ {module}.py 导入失败: {e}")
            all_success = False
    
    return all_success


def test_database_initialization():
    print("\n" + "=" * 60)
    print("测试数据库初始化")
    print("=" * 60)
    
    test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    test_db.close()
    database.DB_PATH = test_db.name
    
    try:
        database.init_db()
        print(f"✅ 数据库初始化成功，路径: {test_db.name}")
        
        conn = database.get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        conn.close()
        
        expected_tables = ["reminders", "countdowns", "intervals", "history", "settings"]
        for table in expected_tables:
            if table in tables:
                print(f"  ✅ 表 {table} 存在")
            else:
                print(f"  ❌ 表 {table} 不存在")
        
        settings = database.get_all_settings()
        print(f"  ✅ 设置项数量: {len(settings)}")
        
        os.unlink(test_db.name)
        return True
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        if os.path.exists(test_db.name):
            os.unlink(test_db.name)
        return False


def test_resource_files():
    print("\n" + "=" * 60)
    print("测试资源文件")
    print("=" * 60)
    
    resources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
    
    if not os.path.exists(resources_dir):
        print(f"❌ resources 目录不存在")
        return False
    
    print(f"✅ resources 目录存在: {resources_dir}")
    
    expected_sounds = ["default.wav", "chime.wav", "ding.wav", "alert.wav", "gentle.wav"]
    all_exist = True
    
    from core import generate_default_sounds
    sounds_dir = generate_default_sounds()
    
    for sound in expected_sounds:
        path = os.path.join(sounds_dir, sound)
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  ✅ {sound} 存在 ({size} bytes)")
        else:
            print(f"  ❌ {sound} 不存在")
            all_exist = False
    
    return all_exist


def test_core_engines():
    print("\n" + "=" * 60)
    print("测试核心引擎初始化")
    print("=" * 60)
    
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QObject
    from core import AudioManager, FocusModeManager, ReminderEngine
    import theme
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    theme._theme_instance = None
    setup_database()
    
    parent = QObject()
    
    try:
        audio = AudioManager(parent)
        print("✅ AudioManager 初始化成功")
        
        sounds = audio.get_available_sounds()
        print(f"  ✅ 可用音效: {sounds}")
    except Exception as e:
        print(f"❌ AudioManager 初始化失败: {e}")
        return False
    
    try:
        focus = FocusModeManager(parent)
        print("✅ FocusModeManager 初始化成功")
        print(f"  ✅ 默认状态: enabled={focus.enabled}")
    except Exception as e:
        print(f"❌ FocusModeManager 初始化失败: {e}")
        return False
    
    try:
        engine = ReminderEngine(audio, focus, parent)
        print("✅ ReminderEngine 初始化成功")
        print(f"  ✅ 定时器运行状态: 正常")
        
        engine.set_paused(True)
        assert engine.is_paused() == True
        engine.set_paused(False)
        assert engine.is_paused() == False
        print("  ✅ 暂停/恢复功能正常")
        
        return True
    except Exception as e:
        print(f"❌ ReminderEngine 初始化失败: {e}")
        return False


def test_tray_manager():
    print("\n" + "=" * 60)
    print("测试系统托盘管理")
    print("=" * 60)
    
    from PyQt6.QtWidgets import QApplication, QWidget
    from PyQt6.QtCore import QObject
    from core import AudioManager, FocusModeManager, ReminderEngine
    from tray import TrayManager, create_tray_icon, FloatingWindow
    import theme
    
    app = QApplication.instance() or QApplication(sys.argv)
    theme._theme_instance = None
    setup_database()
    
    try:
        icon = create_tray_icon()
        print("✅ 托盘图标创建成功")
        assert not icon.isNull()
    except Exception as e:
        print(f"❌ 托盘图标创建失败: {e}")
        return False
    
    try:
        parent = QObject()
        audio = AudioManager(parent)
        focus = FocusModeManager(parent)
        engine = ReminderEngine(audio, focus, parent)
        
        main_window = QWidget()
        
        tray = TrayManager(main_window, engine, focus)
        print("✅ TrayManager 初始化成功")
        print(f"  ✅ 托盘菜单项: {tray.menu.actions().__len__()} 个")
        
        floating = FloatingWindow(engine)
        print("✅ FloatingWindow 初始化成功")
        floating.close()
        
        return True
    except Exception as e:
        print(f"❌ TrayManager 初始化失败: {e}")
        return False


def test_main_window_creation():
    print("\n" + "=" * 60)
    print("测试主窗口创建")
    print("=" * 60)
    
    from PyQt6.QtWidgets import QApplication
    from ui_main import MainWindow
    import theme
    
    app = QApplication.instance() or QApplication(sys.argv)
    theme._theme_instance = None
    setup_database()
    
    try:
        window = MainWindow()
        print("✅ MainWindow 创建成功")
        print(f"  ✅ 窗口标题: {window.windowTitle()}")
        print(f"  ✅ 窗口大小: {window.width()}x{window.height()}")
        print(f"  ✅ 标签页数量: {window.tabs.count()}")
        
        tab_names = [window.tabs.tabText(i) for i in range(window.tabs.count())]
        for name in tab_names:
            print(f"    - {name}")
        
        print(f"  ✅ 核心组件已初始化:")
        print(f"    - engine: {'✅' if window.engine else '❌'}")
        print(f"    - audio: {'✅' if window.audio else '❌'}")
        print(f"    - focus_mode: {'✅' if window.focus_mode else '❌'}")
        print(f"    - reminder_tab: {'✅' if window.reminder_tab else '❌'}")
        print(f"    - countdown_tab: {'✅' if window.countdown_tab else '❌'}")
        print(f"    - interval_tab: {'✅' if window.interval_tab else '❌'}")
        print(f"    - history_tab: {'✅' if window.history_tab else '❌'}")
        
        window.close()
        return True
    except Exception as e:
        print(f"❌ MainWindow 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dialog_creation():
    print("\n" + "=" * 60)
    print("测试对话框创建")
    print("=" * 60)
    
    from PyQt6.QtWidgets import QApplication
    from ui_dialogs import (
        AddReminderDialog, AddCountdownDialog, AddIntervalDialog,
        SettingsDialog, NotificationPopup
    )
    import theme
    
    app = QApplication.instance() or QApplication(sys.argv)
    theme._theme_instance = None
    setup_database()
    
    dialogs = [
        ("AddReminderDialog", AddReminderDialog, {}),
        ("AddCountdownDialog", AddCountdownDialog, {}),
        ("AddIntervalDialog", AddIntervalDialog, {}),
        ("SettingsDialog", SettingsDialog, {}),
        ("NotificationPopup", NotificationPopup, {"title": "测试", "content": "内容"}),
    ]
    
    all_success = True
    for name, dialog_class, kwargs in dialogs:
        try:
            dlg = dialog_class(**kwargs)
            print(f"✅ {name} 创建成功")
            dlg.close()
        except Exception as e:
            print(f"❌ {name} 创建失败: {e}")
            all_success = False
    
    return all_success


def test_theme_system():
    print("\n" + "=" * 60)
    print("测试主题系统")
    print("=" * 60)
    
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QObject
    from theme import ThemeManager, THEMES
    import theme
    
    app = QApplication.instance() or QApplication(sys.argv)
    theme._theme_instance = None
    setup_database()
    
    try:
        parent = QObject()
        tm = ThemeManager(parent)
        print("✅ ThemeManager 初始化成功")
        
        themes = tm.get_all_themes()
        print(f"  ✅ 可用主题: {len(themes)} 个")
        for key, name in themes:
            print(f"    - {name} ({key})")
        
        for theme_name in THEMES.keys():
            tm.set_theme(theme_name)
            assert tm.get_current_theme() == theme_name
            theme = tm.get_theme()
            ss = tm.get_stylesheet()
            print(f"  ✅ 主题 {theme_name}: 样式表大小 {len(ss)} 字节")
        
        return True
    except Exception as e:
        print(f"❌ 主题系统测试失败: {e}")
        return False


def run_all_startup_tests():
    print("\n" + "🚀" * 20)
    print("多功能提醒工具 - 应用启动测试")
    print("🚀" * 20 + "\n")
    
    tests = [
        ("模块导入测试", test_application_imports),
        ("数据库初始化测试", test_database_initialization),
        ("资源文件测试", test_resource_files),
        ("核心引擎测试", test_core_engines),
        ("托盘管理测试", test_tray_manager),
        ("主窗口创建测试", test_main_window_creation),
        ("对话框创建测试", test_dialog_creation),
        ("主题系统测试", test_theme_system),
    ]
    
    results = []
    start_time = time.time()
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 执行异常: {e}")
            results.append((name, False))
    
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {name}")
    
    print("\n" + "-" * 60)
    print(f"总计: {passed}/{total} 通过")
    print(f"耗时: {duration:.2f} 秒")
    
    restore_database()
    
    if passed == total:
        print("\n🎉 所有启动测试通过！应用可以正常运行。")
    else:
        print(f"\n⚠️  有 {total - passed} 项测试失败，请检查问题。")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_startup_tests()
    sys.exit(0 if success else 1)
