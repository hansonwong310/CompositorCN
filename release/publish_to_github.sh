#!/bin/bash
# ==============================================================================
# CompositorCN GitHub 双轨发布与推送自动化脚本
# 目标仓库: https://github.com/hansonwong310/CompositorCN.git
# ==============================================================================

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

REMOTE_URL="https://github.com/hansonwong310/CompositorCN.git"

echo "=================================================================="
echo "  🚀 Compositor 官方全量汉化工程 GitHub 自动化发布工具"
echo "  目标仓库: $REMOTE_URL"
echo "=================================================================="
echo ""

# 1. 配置或更新远程仓库为 HTTPS 地址
echo "📌 [步骤 1/4] 配置 GitHub 远程仓库 (origin -> HTTPS)..."
if git remote | grep -q "^origin$"; then
    git remote set-url origin "$REMOTE_URL"
else
    git remote add origin "$REMOTE_URL"
fi
echo "  [✓] 远程仓库已设置为: $REMOTE_URL"

# 2. 检查并提交本地工作区变更
echo ""
echo "📌 [步骤 2/4] 检查并提交本地汉化成果与发布资产..."
git add -A
if git diff --staged --quiet; then
    echo "  [i] 本地工作区干净，无新增变更待提交"
else
    git commit -m "feat(release): 发布 Compositor 官方全量汉化补丁 v1.0.0 (自包含便携 App + 标准 DMG/ZIP + 全景交接文档)"
    echo "  [✓] 本地版本已提交: $(git log -1 --oneline)"
fi

# 3. 获取远端分支信息并归档原版源码至 upstream 分支
echo ""
echo "📌 [步骤 3/4] 获取远端原版源码并归档至 upstream 分支..."
echo "  [*] 正在执行 git fetch origin 拉取远端分支历史..."
git fetch origin

if git rev-parse --verify origin/main &>/dev/null; then
    echo "  [*] 正在将远端原版 origin/main 推送至 upstream 分支永久归档..."
    git push origin origin/main:refs/heads/upstream
    echo "  [✓] 原版 Robbie Tilton Swift 源码历史已完整保留在 upstream 分支"
else
    echo "  [i] 未检测到远端 origin/main 分支，跳过 upstream 归档"
fi

# 4. 实施双轨共存：推送汉化补丁至 main 与 cn-patch 分支
echo ""
echo "📌 [步骤 4/4] 推送本地汉化补丁至远端 main 与 cn-patch 分支..."
echo "  [*] 正在推送至远端 main 主分支..."
git push -u origin main --force
echo "  [*] 正在同步推送至远端 cn-patch 汉化专有分支..."
git push -u origin main:refs/heads/cn-patch --force
echo "  [✓] 双轨分支 (main & cn-patch) 推送完成！"

echo ""
echo "=================================================================="
echo "🎉 恭喜！汉化工程已成功发布至 GitHub！"
echo "👉 仓库主页: https://github.com/hansonwong310/CompositorCN"
echo "👉 上游原版源码分支 (upstream): https://github.com/hansonwong310/CompositorCN/tree/upstream"
echo "👉 汉化套件主干分支 (main):     https://github.com/hansonwong310/CompositorCN/tree/main"
echo "👉 汉化补丁专有分支 (cn-patch): https://github.com/hansonwong310/CompositorCN/tree/cn-patch"
echo ""
echo "【下一步：发布 GitHub Release v1.0.0】"
echo "1. 打开浏览器访问: https://github.com/hansonwong310/CompositorCN/releases/new"
echo "2. Tag 选择或新建: v1.0.0"
echo "3. 标题输入: Compositor 官方全量汉化补丁 v1.0.0 (Photoshop 标准版)"
echo "4. 同时上传以下两种格式的发布资产文件:"
echo "   - $REPO_DIR/release/Compositor-一键汉化补丁.dmg"
echo "   - $REPO_DIR/release/Compositor-一键汉化补丁.zip"
echo "=================================================================="

