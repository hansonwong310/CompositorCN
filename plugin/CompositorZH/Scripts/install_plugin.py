#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CompositorZH 全量深度汉化插件安装与维护工具
双引擎驱动：
1. 静态引擎：注入 zh-Hans.lproj/Localizable.strings 资源
2. 动态引擎：注入 CompositorZH.dylib 运行时 Hook (拦截 NSSegmentedControl, NSMenuItem, NSButton, NSTextField)
达到 100% 深度彻底汉化！零侵入源码，原应用升级重新运行一行命令即可秒级恢复。
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

def build_binaries_if_needed(plugin_dir):
    dylib_path = plugin_dir / "CompositorZH.dylib"
    launcher_path = plugin_dir / "launcher"
    src_dir = plugin_dir / "Sources/CompositorZH"

    if not dylib_path.exists():
        print("  [*] 正在编译动态库插件 CompositorZH.dylib...")
        subprocess.run([
            "clang", "-shared", "-fPIC", "-framework", "Foundation", "-framework", "AppKit",
            str(src_dir / "CompositorZH.m"), "-o", str(dylib_path)
        ], check=True)

    if not launcher_path.exists():
        print("  [*] 正在编译挂载启动器 launcher...")
        subprocess.run([
            "clang", str(src_dir / "launcher.c"), "-o", str(launcher_path)
        ], check=True)

def install_plugin(app_path):
    print(f"=== 开始为 Compositor 部署全量深度汉化插件 ===")
    print(f"目标应用: {app_path}")
    
    macos_dir = app_path / "Contents/MacOS"
    resources_dir = app_path / "Contents/Resources"
    info_plist_path = app_path / "Contents/Info.plist"

    if not macos_dir.exists() or not resources_dir.exists():
        print(f"[错误] App 目录损坏: {app_path}")
        return False

    plugin_dir = get_plugin_dir()
    build_binaries_if_needed(plugin_dir)

    src_lproj = plugin_dir / "zh-Hans.lproj"
    dest_lproj = resources_dir / "zh-Hans.lproj"
    if dest_lproj.exists():
        shutil.rmtree(dest_lproj)
    shutil.copytree(src_lproj, dest_lproj)
    print("  [✓] 静态资源包注入完成 (500+ Photoshop 标准词条)")

    dylib_src = plugin_dir / "CompositorZH.dylib"
    launcher_src = plugin_dir / "launcher"
    
    dylib_dest = macos_dir / "CompositorZH.dylib"
    app_bin = macos_dir / "Compositor"
    app_bin_raw = macos_dir / "Compositor_raw"

    if not app_bin_raw.exists():
        if app_bin.exists():
            shutil.copyfile(app_bin, app_bin_raw)
            os.chmod(app_bin_raw, 0o755)
            print("  [✓] 原版主程序已建立物理备份 -> Compositor_raw")
    
    shutil.copyfile(dylib_src, dylib_dest)
    os.chmod(dylib_dest, 0o755)

    shutil.copyfile(launcher_src, app_bin)
    os.chmod(app_bin, 0o755)
    print("  [✓] 动态 Runtime Hook 插件已注入 (拦截选项栏/分段按钮/动态撤销)")

    if info_plist_path.exists():
        try:
            with open(info_plist_path, "rb") as f:
                plist_data = plistlib.load(f)
            locs = plist_data.get("CFBundleLocalizations", [])
            if "zh-Hans" not in locs:
                locs.append("zh-Hans")
                plist_data["CFBundleLocalizations"] = locs
                with open(info_plist_path, "wb") as f:
                    plistlib.dump(plist_data, f)
                print("  [✓] Info.plist 已注册 zh-Hans 语言支持")
        except Exception as e:
            print(f"  [!] Info.plist 更新警告: {e}")

    print("  [*] 正在执行 Ad-hoc 签名以通过系统安全检测...")
    try:
        subprocess.run(
            ["codesign", "--force", "--deep", "--sign", "-", str(app_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("  [✓] 签名刷新完成！")
    except Exception as e:
        print(f"  [!] codesign 警告: {e}")

    print("\n🎉 全量深度汉化插件安装成功！双引擎已全部就绪。")
    return True

def uninstall_plugin(app_path):
    print(f"=== 正在卸载 Compositor 汉化插件 ===")
    macos_dir = app_path / "Contents/MacOS"
    resources_dir = app_path / "Contents/Resources"

    dest_lproj = resources_dir / "zh-Hans.lproj"
    if dest_lproj.exists():
        shutil.rmtree(dest_lproj)
        print("  [✓] 语言包已移除")

    dylib_dest = macos_dir / "CompositorZH.dylib"
    if dylib_dest.exists():
        dylib_dest.unlink()
        print("  [✓] 动态库插件已移除")

    app_bin = macos_dir / "Compositor"
    app_bin_raw = macos_dir / "Compositor_raw"
    if app_bin_raw.exists():
        shutil.copyfile(app_bin_raw, app_bin)
        os.chmod(app_bin, 0o755)
        app_bin_raw.unlink()
        print("  [✓] 主程序已完全还原为原版官方二进制")

    try:
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app_path)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        pass

    print("已成功彻底恢复纯英文官方原版状态。")
    return True

def main():
    parser = argparse.ArgumentParser(description="Compositor 全量深度汉化插件管理器")
    parser.add_argument("--app", help="指定 Compositor.app 的绝对路径", default=None)
    parser.add_argument("--install", action="store_true", help="安装汉化插件 (默认动作)")
    parser.add_argument("--uninstall", action="store_true", help="卸载汉化插件")

    args = parser.parse_args()
    app_path = find_app_path(args.app)

    if not app_path:
        print("[错误] 未找到已安装的 Compositor.app")
        return

    if args.uninstall:
        uninstall_plugin(app_path)
    else:
        install_plugin(app_path)

if __name__ == "__main__":
    main()
