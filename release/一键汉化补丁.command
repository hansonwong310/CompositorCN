#!/bin/bash
cd "$(dirname "$0")"

echo "=================================================="
echo "    Compositor 官方汉化补丁 (Photoshop 标准版)     "
echo "=================================================="
echo ""
echo "正在检测 Compositor.app..."

SCRIPT_DIR="$(dirname "$0")"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALLER="$PROJECT_DIR/plugin/CompositorZH/Scripts/install_plugin.py"

if [ ! -f "$INSTALLER" ]; then
    INSTALLER="$(cd "$SCRIPT_DIR" && pwd)/install_plugin.py"
fi

if [ -f "$INSTALLER" ]; then
    python3 "$INSTALLER"
    if [ $? -eq 0 ]; then
        echo ""
        echo "=================================================="
        echo "🎉 恭喜！汉化补丁安装成功！"
        echo "已自动为您启动 Compositor，尽情享受中文版吧！"
        echo "=================================================="
        open /Applications/Compositor.app 2>/dev/null
    else
        echo "安装过程中出现错误，请检查权限。"
    fi
else
    echo "未找到安装脚本组件，请确保文件完整。"
fi

echo ""
read -n 1 -s -r -p "按任意键退出窗口..."
echo ""
