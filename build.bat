@echo off
chcp 65001
echo ========================================
echo  多功能提醒工具 - 打包脚本 (Windows)
echo ========================================
echo.

echo [1/3] 安装依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo 依赖安装失败！
    pause
    exit /b 1
)

echo.
echo [2/3] 开始打包...
pyinstaller --noconfirm --clean ReminderTool.spec
if errorlevel 1 (
    echo 打包失败！
    pause
    exit /b 1
)

echo.
echo [3/3] 打包完成！
echo 可执行文件位于 dist\ReminderTool\
echo.
pause
