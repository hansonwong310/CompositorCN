#!/bin/bash
# ==============================================================================
# 双击运行：CompositorCN 一键发布到 GitHub 交互式引导工具
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

clear
bash "$SCRIPT_DIR/publish_to_github.sh"

echo ""
read -r -p "按 [回车键 Enter] 关闭此窗口..." _
