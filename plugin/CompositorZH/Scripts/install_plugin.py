#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CompositorZH 独立汉化插件安装与管理工具
设计目标：
1. 最小侵入：不修改任何源码，不破坏项目结构。
2. 升级无损：原项目通过 Homebrew 或 GitHub Releases 升级后，重新运行本脚本即可恢复汉化。
3. 绿色卸载：提供一键恢复原生纯英文状态机制。
"""

import os
import sys
import shutil
import subprocess
import argparse
import plistlib
from pathlib import Path

DEFAULT_APP_PATHS = [
    Path("/Applications/Compositor.app"),
    Path.home() / "Applications/Compositor.app",
    Path("./Compositor.app")
]

def find_app_path(custom_path=None):
    if custom_path:
        p = Path(custom_path).resolve()
        if p.exists() and p.name.endswith(".app"):
            return p
        print(f"[错误] 指定路径未找到有效的 Compositor.app: {custom_path}")
        return None

    for candidate in DEFAULT_APP_PATHS:
        if candidate.exists():
            return candidate
    return None

def get_plugin_dir():
    return Path(__file__).resolve().parent.parent

def install_plugin(app_path):
    print(f"=== 开始为 Compositor 安装汉化插件 ===")
    print(f"目标应用: {app_path}")
    
    resources_dir = app_path / "Contents/Resources"
    info_plist_path = app_path / "Contents/Info.plist"

    if not resources_dir.exists():
        print(f"[错误] Resources 目录不存在: {resources_dir}")
        return False

    plugin_dir = get_plugin_dir()
    src_lproj = plugin_dir / "zh-Hans.lproj"

    if not src_lproj.exists():
        print(f"[错误] 插件语言包不存在: {src_lproj}")
        return False

    dest_lproj = resources_dir / "zh-Hans.lproj"
    
    # 1. 拷贝语言包
    if dest_lproj.exists():
        shutil.rmtree(dest_lproj)
    shutil.copytree(src_lproj, dest_lproj)
    print(f"  [✓] 成功注入语言包 -> {dest_lproj}")

    # 2. 更新 Info.plist 支持本地化声明
    if info_plist_path.exists():
        try:
            with open(info_plist_path, "rb") as f:
                plist_data = plistlib.load(f)
            
            # 备份原始 Info.plist
            backup_plist = app_path / "Contents/Info.plist.orig"
            if not backup_plist.exists():
                shutil.copyfile(info_plist_path, backup_plist)

            locs = plist_data.get("CFBundleLocalizations", [])
            if "zh-Hans" not in locs:
                locs.append("zh-Hans")
                plist_data["CFBundleLocalizations"] = locs
                with open(info_plist_path, "wb") as f:
                    plistlib.dump(plist_data, f)
                print("  [✓] 成功在 Info.plist 中注册 zh-Hans 本地化语言支持")
        except Exception as e:
            print(f"  [!] 更新 Info.plist 时出现警告: {e}")

    # 3. 重新签署 Ad-hoc 签名以防止 macOS Gatekeeper 拦截
    print("  [*] 正在执行 Ad-hoc 代码签名...")
    try:
        subprocess.run(
            ["codesign", "--force", "--deep", "--sign", "-", str(app_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("  [✓] 签名刷新完成！应用可正常双击启动。")
    except Exception as e:
        print(f"  [!] codesign 警告（如无权限可忽略）: {e}")

    print("\n恭喜！Compositor 汉化插件安装成功！启动应用即可体验全中文 PS 专业术语界面。")
    return True

def uninstall_plugin(app_path):
    print(f"=== 正在卸载 Compositor 汉化插件 ===")
    print(f"目标应用: {app_path}")

    dest_lproj = app_path / "Contents/Resources/zh-Hans.lproj"
    if dest_lproj.exists():
        shutil.rmtree(dest_lproj)
        print("  [✓] 汉化资源包已移除")

    backup_plist = app_path / "Contents/Info.plist.orig"
    info_plist_path = app_path / "Contents/Info.plist"
    if backup_plist.exists():
        shutil.copyfile(backup_plist, info_plist_path)
        backup_plist.unlink()
        print("  [✓] Info.plist 已还原为原始状态")

    try:
        subprocess.run(
            ["codesign", "--force", "--deep", "--sign", "-", str(app_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except Exception:
        pass

    print("Compositor 现已完全恢复为纯英文原生状态。")
    return True

def check_status(app_path):
    print(f"=== Compositor 汉化状态检查 ===")
    print(f"应用路径: {app_path}")
    dest_lproj = app_path / "Contents/Resources/zh-Hans.lproj"
    if dest_lproj.exists():
        print("状态: 【已启用汉化】 (zh-Hans.lproj 存在)")
    else:
        print("状态: 【未启用汉化】 (原生英文版本)")

def main():
    parser = argparse.ArgumentParser(description="Compositor 独立汉化插件管理器")
    parser.add_argument("--app", help="指定 Compositor.app 的绝对路径", default=None)
    parser.add_argument("--install", action="store_true", help="安装汉化插件 (默认动作)")
    parser.add_argument("--uninstall", action="store_true", help="卸载汉化插件")
    parser.add_argument("--status", action="store_true", help="查看汉化状态")

    args = parser.parse_args()
    app_path = find_app_path(args.app)

    if not app_path:
        print("[提示] 本地尚未检测到已安装的 Compositor.app。")
        print("您可通过 Homebrew 安装: brew install --cask robbietilton-compositor")
        print("或从 GitHub Releases 下载后，再次运行本命令安装汉化：")
        print(f"python3 {__file__} --app /path/to/Compositor.app")
        return

    if args.uninstall:
        uninstall_plugin(app_path)
    elif args.status:
        check_status(app_path)
    else:
        install_plugin(app_path)

if __name__ == "__main__":
    main()
