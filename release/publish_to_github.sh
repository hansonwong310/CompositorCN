#!/bin/bash
# ==============================================================================
# CompositorCN GitHub 双轨发布与推送自动化脚本
# 目标仓库: https://github.com/hansonwong310/CompositorCN.git
# 用法:
#   1. 双击运行 release/一键发布到GitHub.command（交互式引导）
#   2. 终端非阻塞执行: bash release/publish_to_github.sh --auto
#   3. 传入 Token 执行: bash release/publish_to_github.sh <GitHub_PAT_Token>
# ==============================================================================

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

HTTPS_URL="https://github.com/hansonwong310/CompositorCN.git"
SSH_URL="git@github.com:hansonwong310/CompositorCN.git"
ORIG_UPSTREAM_SHA="f5ae5bad0b25b32dda9f254e62d2f07f59478698"

AUTO_MODE=0
INPUT_TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
if [ "${1:-}" = "--auto" ]; then
    AUTO_MODE=1
elif [ -n "${1:-}" ]; then
    INPUT_TOKEN="$1"
fi

echo "=================================================================="
echo "  🚀 Compositor 官方全量汉化工程 GitHub 自动化发布工具"
echo "  目标仓库: https://github.com/hansonwong310/CompositorCN"
echo "=================================================================="
echo ""

# 1. 自动构建本地 upstream 分支指向原版源码 (origin/main)
echo "📌 [步骤 1/4] 绑定本地 upstream 分支（保护原版 Swift 源码历史）..."
if git cat-file -e "${ORIG_UPSTREAM_SHA}^{commit}" 2>/dev/null; then
    git branch -f upstream "$ORIG_UPSTREAM_SHA"
    echo "  [✓] 已构建本地 upstream 分支 -> $ORIG_UPSTREAM_SHA (Robbie Tilton 原版源码)"
elif git rev-parse --verify origin/main &>/dev/null; then
    git branch -f upstream origin/main
    echo "  [✓] 已构建本地 upstream 分支 -> origin/main ($(git rev-parse --short origin/main))"
else
    git fetch origin || true
    if git rev-parse --verify origin/main &>/dev/null; then
        git branch -f upstream origin/main
        echo "  [✓] 已拉取并构建本地 upstream 分支 -> origin/main"
    fi
fi

# 2. 检查并提交本地工作区变更，同时绑定 cn-patch 分支与 v1.0.0 标签
echo ""
echo "📌 [步骤 2/4] 检查并提交本地汉化成果，同步 cn-patch 分支与 v1.0.0 标签..."
git add -A
if git diff --staged --quiet; then
    echo "  [i] 本地工作区干净，无新增变更待提交"
else
    git commit -m "feat(release): 发布 Compositor 官方全量汉化补丁 v1.0.0 (自包含便携 App + 标准 DMG/ZIP + 全景交接文档)"
    echo "  [✓] 本地版本已提交: $(git log -1 --oneline)"
fi

git branch -f cn-patch main
git tag -f v1.0.0 main
echo "  [✓] 本地分支与标签已就绪: upstream (原版源码) | main (汉化主干) | cn-patch (汉化专有) | tag: v1.0.0"

# 3. 智能认证检测与自动修复 (SSH / HTTPS PAT)
echo ""
echo "📌 [步骤 3/4] 检测 GitHub 推送认证通道..."

AUTH_READY=0
PUSH_REMOTE_URL="$HTTPS_URL"

save_pat_to_keychain() {
    local token="$1"
    printf "protocol=https\nhost=github.com\n\n" | git credential-osxkeychain erase 2>/dev/null || true
    printf "protocol=https\nhost=github.com\nusername=hansonwong310\n\n" | git credential-osxkeychain erase 2>/dev/null || true
    printf "protocol=https\nhost=github.com\nusername=hansonwong310\npassword=%s\n\n" "$token" | git credential-osxkeychain store 2>/dev/null || true
    git remote set-url origin "$HTTPS_URL"
    PUSH_REMOTE_URL="https://hansonwong310:${token}@github.com/hansonwong310/CompositorCN.git"
    AUTH_READY=1
}

# 3.1 若传入了 Token 参数或环境变量，直接应用
if [ -n "$INPUT_TOKEN" ]; then
    echo "  [*] 检测到传入的 GitHub Token，正在更新钥匙串凭据..."
    save_pat_to_keychain "$INPUT_TOKEN"
    echo "  [✓] GitHub PAT 凭据已配置就绪"
fi

# 3.2 扫描 ~/.ssh/ 下所有私钥并测试 SSH 免密连通性
if [ "$AUTH_READY" -eq 0 ]; then
    ssh-add --apple-load-keychain 2>/dev/null || true
    shopt -s nullglob
    for keyfile in "$HOME"/.ssh/id_* "$HOME"/.ssh/*github* "$HOME"/.ssh/*git*; do
        case "$keyfile" in
            *.pub|*known_hosts*|*config*|*authorized_keys*) continue ;;
        esac
        if [ -f "$keyfile" ]; then
            ssh-add "$keyfile" 2>/dev/null || true
        fi
    done
    shopt -u nullglob

    SSH_CHECK=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 || true)
    if echo "$SSH_CHECK" | grep -qi "successfully authenticated"; then
        echo "  [✓] SSH 密钥认证通过 ($SSH_CHECK)"
        git remote set-url origin "$SSH_URL"
        PUSH_REMOTE_URL="$SSH_URL"
        AUTH_READY=1
    fi
fi

# 3.3 若未通过认证：区分非阻塞模式 (--auto / 非交互终端) 与交互式终端
if [ "$AUTH_READY" -eq 0 ]; then
    if [ "$AUTO_MODE" -eq 1 ] || [ ! -t 0 ]; then
        echo "  [!] 当前 SSH 尚未在 GitHub 授权，且钥匙串中的 HTTPS 旧凭据已过期。"
        if [ ! -f "$HOME/.ssh/id_ed25519.pub" ] && [ ! -f "$HOME/.ssh/id_rsa.pub" ]; then
            ssh-keygen -t ed25519 -C "hansonwong310@hotmail.com" -f "$HOME/.ssh/id_ed25519" -N "" >/dev/null 2>&1 || true
        fi
        PUB_KEY_FILE="$HOME/.ssh/id_ed25519.pub"
        [ ! -f "$PUB_KEY_FILE" ] && PUB_KEY_FILE="$HOME/.ssh/id_rsa.pub"
        if [ -f "$PUB_KEY_FILE" ]; then
            pbcopy < "$PUB_KEY_FILE" 2>/dev/null || true
            ssh-add "${PUB_KEY_FILE%.pub}" 2>/dev/null || true
            echo "  [✓] 已自动将本机 SSH 公钥复制到系统剪贴板！"
            echo "  🔑 SSH 公钥: $(cat "$PUB_KEY_FILE")"
        fi
        echo ""
        echo "  👉 本地分支 (upstream / main / cn-patch) 与标签 (v1.0.0) 已 100% 构建完毕！"
        echo "  👉 请任选以下一种方式完成最后一步推送："
        echo "     • 方法 A（推荐）：在 Finder 中双击运行 release/一键发布到GitHub.command"
        echo "     • 方法 B（SSH 免密）：打开 https://github.com/settings/ssh/new 按 Cmd+V 粘贴剪贴板中的公钥保存，然后重新运行本脚本"
        exit 0
    fi

    echo "  [!] 检测到当前 SSH 未加载有效公钥，且 macOS 钥匙串中的 GitHub HTTPS 凭据已失效。"
    echo ""
    echo "  请选择认证方式完成推送："
    echo "    [1] 输入 GitHub Personal Access Token (PAT) 自动修复钥匙串并推送（推荐）"
    echo "    [2] 自动复制本机 SSH 公钥并打开 GitHub 设置页添加后推送"
    echo ""
    read -r -p "  请输入选项 [1/2，默认 1]: " AUTH_CHOICE
    AUTH_CHOICE="${AUTH_CHOICE:-1}"

    if [ "$AUTH_CHOICE" = "2" ]; then
        if [ ! -f "$HOME/.ssh/id_ed25519.pub" ] && [ ! -f "$HOME/.ssh/id_rsa.pub" ]; then
            echo "  [*] 正在为您生成本机 SSH 密钥 (id_ed25519)..."
            ssh-keygen -t ed25519 -C "hansonwong310@hotmail.com" -f "$HOME/.ssh/id_ed25519" -N ""
        fi
        PUB_KEY_FILE="$HOME/.ssh/id_ed25519.pub"
        [ ! -f "$PUB_KEY_FILE" ] && PUB_KEY_FILE="$HOME/.ssh/id_rsa.pub"
        pbcopy < "$PUB_KEY_FILE"
        ssh-add "${PUB_KEY_FILE%.pub}" 2>/dev/null || true
        echo ""
        echo "  [✓] 您的 SSH 公钥已自动复制到剪贴板！"
        echo "  公钥内容: $(cat "$PUB_KEY_FILE")"
        open "https://github.com/settings/ssh/new" 2>/dev/null || true
        echo "  👉 已为您打开 GitHub SSH Keys 添加页面，请在网页中按 Cmd+V 粘贴并保存。"
        read -r -p "  添加完成后请按 [回车键 Enter] 继续推送..." _
        git remote set-url origin "$SSH_URL"
        PUSH_REMOTE_URL="$SSH_URL"
    else
        echo ""
        echo "  💡 提示：如果您还没有 Token，正在为您打开 GitHub Token 一键生成页面（勾选 repo 权限即可）..."
        open "https://github.com/settings/tokens/new?scopes=repo&description=CompositorCN-Release" 2>/dev/null || true
        read -r -s -p "  请粘贴您的 GitHub Personal Access Token (输入过程隐藏，完成后按回车): " USER_PAT
        echo ""
        if [ -z "$USER_PAT" ]; then
            echo "  [✗] 未输入 Token，操作已取消。"
            exit 1
        fi
        save_pat_to_keychain "$USER_PAT"
        echo "  [✓] 新 Token 已写入 macOS 钥匙串并清除旧失效凭据！"
    fi
fi

# 4. 执行双轨分支与标签推送 (upstream + main + cn-patch + v1.0.0)
echo ""
echo "📌 [步骤 4/4] 执行双轨分支与 v1.0.0 标签推送..."

echo "  [*] (1/4) 正在将原版 Swift 源码历史推送至远端 upstream 分支保护..."
git push "$PUSH_REMOTE_URL" refs/heads/upstream:refs/heads/upstream --force
echo "  [✓] 远端 upstream 分支已完整保存 Robbie Tilton 原版源码历史"

echo "  [*] (2/4) 正在将本地汉化补丁推送至远端 main 主分支..."
git push "$PUSH_REMOTE_URL" refs/heads/main:refs/heads/main --force
git branch --set-upstream-to=origin/main main 2>/dev/null || true

echo "  [*] (3/4) 正在同步推送至远端 cn-patch 汉化专有分支..."
git push "$PUSH_REMOTE_URL" refs/heads/main:refs/heads/cn-patch --force

echo "  [*] (4/4) 正在推送版本标签 v1.0.0..."
git push "$PUSH_REMOTE_URL" refs/tags/v1.0.0:refs/tags/v1.0.0 --force

if [[ "$PUSH_REMOTE_URL" == https://* ]]; then
    git remote set-url origin "$HTTPS_URL"
fi

echo "  [✓] 三大分支 (upstream / main / cn-patch) 与标签 (v1.0.0) 全部推送完成！"

echo ""
echo "=================================================================="
echo "🎉 恭喜！Compositor 汉化工程已成功发布至 GitHub！"
echo "👉 仓库主页: https://github.com/hansonwong310/CompositorCN"
echo "👉 上游原版源码分支 (upstream): https://github.com/hansonwong310/CompositorCN/tree/upstream"
echo "👉 汉化套件主干分支 (main):     https://github.com/hansonwong310/CompositorCN/tree/main"
echo "👉 汉化补丁专有分支 (cn-patch): https://github.com/hansonwong310/CompositorCN/tree/cn-patch"
echo ""
echo "【下一步：发布 GitHub Release v1.0.0】"
echo "1. 打开浏览器访问: https://github.com/hansonwong310/CompositorCN/releases/new?tag=v1.0.0"
echo "2. 标题输入: Compositor 官方全量汉化补丁 v1.0.0 (Photoshop 标准版)"
echo "3. 同时上传以下两种格式的发布资产文件:"
echo "   - $REPO_DIR/release/Compositor-一键汉化补丁.dmg"
echo "   - $REPO_DIR/release/Compositor-一键汉化补丁.zip"
echo "=================================================================="
