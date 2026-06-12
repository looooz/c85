import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

import database
from ui_main import MainWindow
from tray import TrayManager


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("多功能提醒工具")
    app.setApplicationDisplayName("多功能提醒工具")
    app.setQuitOnLastWindowClosed(False)

    database.init_db()

    try:
        window = MainWindow()
    except Exception as e:
        QMessageBox.critical(None, "启动错误", f"程序启动失败：{str(e)}")
        sys.exit(1)

    tray = TrayManager(window, window.engine, window.focus_mode)
    window.tray_manager = tray

    window.reminder_triggered_signal.connect(
        lambda data: tray.show_notification("提醒", data["title"])
    )
    window.countdown_triggered_signal.connect(
        lambda data: tray.show_notification("倒计时结束", data["title"])
    )
    window.interval_triggered_signal.connect(
        lambda data: tray.show_notification("间隔提醒", data["title"])
    )
    window.hourly_chime_signal.connect(
        lambda: tray.show_notification("整点报时", "整点了！")
    )

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
