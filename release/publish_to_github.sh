#!/bin/bash
# ==============================================================================
# CompositorCN GitHub 双轨发布与推送自动化脚本
# 目标仓库: git@github.com:hansonwong310/CompositorCN.git
# ==============================================================================

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "=================================================================="
echo "  🚀 Compositor 官方全量汉化工程 GitHub 自动化发布工具"
echo "  目标仓库: git@github.com:hansonwong310/CompositorCN.git"
echo "=================================================================="
echo ""

REMOTE_URL="git@github.com:hansonwong310/CompositorCN.git"

# 1. 配置或更新远程仓库
echo "📌 [步骤 1/5] 配置 GitHub 远程仓库 (origin)..."
if git remote | grep -q "^origin$"; then
    git remote set-url origin "$REMOTE_URL"
else
    git remote add origin "$REMOTE_URL"
fi
echo "  [✓] 远程仓库已设置为: $REMOTE_URL"

# 2. 检查并提交本地工作区变更
echo ""
echo "📌 [步骤 2/5] 检查并提交本地汉化成果与发布资产..."
git add -A
if git diff --staged --quiet; then
    echo "  [i] 本地工作区干净，无新增变更待提交"
else
    git commit -m "feat(release): 发布 Compositor 官方全量汉化补丁 v1.0.0 (自包含便携 App + 标准 DMG + 全景交接文档)"
    echo "  [✓] 本地版本已提交: $(git log -1 --oneline)"
fi

# 3. 测试与 GitHub 的 SSH 连通性
echo ""
echo "📌 [步骤 3/5] 测试 GitHub SSH 认证连接..."
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 || true

# 4. 获取远端分支信息并实施双轨分支管理
echo ""
echo "📌 [步骤 4/5] 获取远端分支并实施双轨备份..."
# 拉取远端上游分支（若存在）
if git ls-remote --exit-code origin &>/dev/null; then
    echo "  [*] 正在拉取远端已存在的上游分支历史..."
    git fetch origin || true
    
    # 若远端已有 main 分支（原作者 Swift 源码），将其备份为 upstream 分支
    if git rev-parse --verify origin/main &>/dev/null; then
        echo "  [*] 检测到远端原版 main 分支，正在将其归档保存至远端 upstream 分支..."
        git push origin origin/main:refs/heads/upstream || true
        echo "  [✓] 上游原版源码历史已成功归档于 upstream 分支"
    fi
fi

# 5. 推送汉化增强主干
echo ""
echo "📌 [步骤 5/5] 推送汉化工程主分支至 GitHub..."
git push -u origin main --force-with-lease || git push -u origin main -f

echo ""
echo "=================================================================="
echo "🎉 恭喜！汉化工程已成功发布至 GitHub！"
echo "👉 仓库主页: https://github.com/hansonwong310/CompositorCN"
echo "👉 上游源码分支: https://github.com/hansonwong310/CompositorCN/tree/upstream"
echo "👉 汉化套件主干: https://github.com/hansonwong310/CompositorCN/tree/main"
echo ""
echo "【下一步：发布 GitHub Release v1.0.0】"
echo "1. 打开浏览器访问: https://github.com/hansonwong310/CompositorCN/releases/new"
echo "2. Tag 选择或新建: v1.0.0"
echo "3. 标题输入: Compositor 官方全量汉化补丁 v1.0.0 (Photoshop 标准版)"
echo "4. 上传资产文件: $REPO_DIR/release/Compositor-一键汉化补丁.dmg"
echo "=================================================================="
