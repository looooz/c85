#!/bin/bash

echo "========================================"
echo " 多功能提醒工具 - 打包脚本 (macOS/Linux)"
echo "========================================"
echo ""

echo "[1/3] 安装依赖..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "依赖安装失败！"
    exit 1
fi

echo ""
echo "[2/3] 开始打包..."
pyinstaller --noconfirm --clean ReminderTool.spec
if [ $? -ne 0 ]; then
    echo "打包失败！"
    exit 1
fi

echo ""
echo "[3/3] 打包完成！"
echo "可执行文件位于 dist/"
echo ""
